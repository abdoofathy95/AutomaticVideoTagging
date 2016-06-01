from __future__ import division
import pickle
import psycopg2
import machine_learning_naivebayes as mln
import operator
from rake import rake
import sys
import re


conn = psycopg2.connect("dbname=datasets user=abdoo") # connect to database
cursor = conn.cursor() # connect to database
match_apostrophes = re.compile(r'[\']+')
def createTable(n):
	query = ' CREATE TABLE %s' %(n) + '''(
				id SERIAL PRIMARY KEY,
				text_id integer REFERENCES krapivin_text (id),
				tag varchar
				);
			'''
	cursor.execute(query)
	conn.commit()

def appendWordToTag(word,id,table):
	query1 = "SELECT tag FROM "+table+" WHERE id = (%s);" %(id)
	cursor.execute(query1)
	conn.commit()
	oldTag = cursor.fetchone()[0]
	newTag = oldTag+' '+word
	newTag = match_apostrophes.sub("\"", newTag)
	query2 = "UPDATE "+table+" SET tag=\'%s\' WHERE id = (%s);" %(newTag,id)
	cursor.execute(query2)
	conn.commit()

def start_naive_bayes_tagging(table):
	# query = "SELECT id,title,text FROM hulth WHERE id > 1000;"
	query = "SELECT id,title,text FROM krapivin_text;"
	query2 = "INSERT INTO "+table+"(text_id,tag) VALUES (%s,%s) RETURNING id;"
	cursor.execute(query)
	conn.commit()
	results = cursor.fetchall()
	test_set = results
	classifier = pickle.load(open('naivebayes_classifier.cls'))
	# classifier.show_most_informative_features(200)
	try:
		createTable(table)
	except:
		conn.rollback()
		cursor.execute("Truncate "+ table +";")
		conn.commit()
		print "Table Already Exists!! \nContinuing with Execution..."
	for index,result in enumerate(test_set):
		print "Progress: "+ str("{0:.2f}".format(index/len(test_set) * 100)) + '%'
		abstractId = result[0]
		title = result[1]
		text = result[2]
		abstract = mln.preprocess(text)
		tags_count = 0
		maximal = mln.getMaxScore(abstract)
		prev_word_tag = False # initialy false meaning not a tag
		prev_word_id = 0
 		for index,word in enumerate(abstract):
			prev_word = abstract[index-1] if index-1 >= 0 else mln.Word('')
			next_word = abstract[index+1] if index+1 < len(abstract) else mln.Word('')
			second_prev_word = abstract[index-2] if index-2 >= 0 else mln.Word('')
			second_next_word = abstract[index+2] if index+2 < len(abstract) else mln.Word('')
			ruling = classifier.classify(
				mln.extract_features(
					abstractId,text,abstract,title,maximal,word,index,prev_word,next_word,second_prev_word,second_next_word))
			
			if ruling == 'Tag' :
				# write to database with checking the index
				if prev_word_tag : 
					appendWordToTag(word.string,prev_word_id,table)
				else:
					data = (int(abstractId),word.string)
					cursor.execute(query2,data)
					conn.commit()
					prev_word_tag = True 
					prev_word_id = int(cursor.fetchone()[0])
					tags_count += 1
			else:
					prev_word_tag = False
	print "Filtering Dataset , Please Wait ..."
	# for i in range(5,15+1):
	# 	list = filterCandidateKeywords(table,i)
	# 	print "DONE !!!!!"
	list = filterCandidateKeywords(table,6)

def start_svm_tagging(table,n):
	table = table + "_" + str(n)
	query = "SELECT id,title,text FROM hulth WHERE id > 1000;"
	# query = "SELECT id,title,text FROM krapivin_text;"
	query2 = "INSERT INTO "+table+"(text_id,tag) VALUES (%s,%s) RETURNING id;"
	cursor.execute(query)
	conn.commit()
	results = cursor.fetchall()
	test_set = results
	classifier = pickle.load(open('svm_classifier.cls'))
	vectorizer = pickle.load(open('svm_vectorizer.vectorizer'))

	try:
		createTable(table)
	except:
		conn.rollback()
		cursor.execute("Truncate "+ table +";")
		conn.commit()
		print "Table Already Exists!! \nContinuing with Execution..."
	for index,result in enumerate(test_set):
		print "Progress: "+ str("{0:.2f}".format(index/len(test_set) * 100)) + '%'
		abstractId = result[0]
		title = result[1]
		text = result[2]
		abstract = mln.preprocess(text)
		tags_count = 0
		maximal = mln.getMaxScore(abstract)
		prev_word_tag = False # initialy false meaning not a tag
		prev_word_id = 0
		feature_test_set= []
		if len(abstract) < 1:
			continue
 		for index,word in enumerate(abstract):
			prev_word = abstract[index-1] if index-1 >= 0 else mln.Word('')
			next_word = abstract[index+1] if index+1 < len(abstract) else mln.Word('')
			second_prev_word = abstract[index-2] if index-2 >= 0 else mln.Word('')
			second_next_word = abstract[index+2] if index+2 < len(abstract) else mln.Word('')
			feature_test_set.append(
				(mln.extract_features(
					abstractId,text,abstract,title,maximal,word,index,prev_word,next_word,second_prev_word,second_next_word)))
		
		vectorized_features = vectorizer.transform(feature_test_set)
		rankArray = classifier.rank(vectorized_features) # returns an array of ranks
		resultKeywords = createWordRankPairArray(abstract,rankArray,n) # create a sorted array of pairs (word,rank) according to rank (Ascending)
		writeToTable(table,resultKeywords,abstractId)


def createWordRankPairArray(wordArray,rankArray,limit):
	'''
	returns: single words with their ranks and index in the original text
	'''
	result = [(word.string, rank, index) for index,(word,rank) in enumerate(zip(wordArray,rankArray))]
	result.sort(key=lambda tup: tup[1],reverse=True)
	return [a for (a,b,c) in result[:limit]]

def sortAccordingToScore(list,phrase_list):
	scores = {}
	for tag in list:
		scores[tag] = getTagScore(tag,phrase_list)
	sorted_list = sorted(scores.items(),key=operator.itemgetter(1),reverse=False)
	sorted_list = [x[0] for x in sorted_list]
	return sorted_list

def getTagScore(tag,phrase_list):
	word_list = tag.split(' ')
	scores = {}
	for word in word_list:
		scores[word] = getWordScore(word,phrase_list)
	score = sum(scores.values())
	return score

def getWordScore(word,phrase_list):
	freq = 0
	degree = 0
	result = getWordPhrases(word,phrase_list)
	phrase_list = result[0]
	length = result[1]
	freq += len(phrase_list)
	degree += length
	try:
		score = ( 1.0 * degree ) / (1.0 * freq )
	except:
		score = 0
	return score

def getAllPhrases(text):
	sentence_list = rake.split_sentences(text)
	return sentence_list

def getWordPhrases(word,phrase_list):
	result_list = []
	length = 0
	for phrase in phrase_list:
		word_list = rake.separate_words(phrase,0)
		l = len(word_list)
		if word in word_list:
			result_list.append(phrase)
			length+=l
	return (result_list,length)

def writeToTable(table,list,text_id):
	query = "INSERT INTO "+table+"(text_id,tag) VALUES (%s,%s);"
	for tag in list:
		data = (text_id,tag)
		cursor.execute(query,data)
		conn.commit()

def fetchCandidateKeywords(table,n):
	query = "SELECT tag FROM %s WHERE text_id = %s;" %(table,n)
	cursor.execute(query)
	conn.commit()
	results = cursor.fetchall()
	tags = []
	for result in results:
		tags.append(result[0])
	return tags

def getText(text_id):
	query = "SELECT text FROM krapivin_text WHERE id = %s;" %(text_id)
	cursor.execute(query)
	conn.commit()
	return cursor.fetchall()[0][0] 

def filterCandidateKeywords(table,number):
	'''
	IDEA: for each text, get the tags , apply filter , then write to new filtered table 
	@param number: (int)number of tags per document
	@return [] String: filtered list where that list is sorted by the score of each tag
	'''
	originalTable = table
	table = table+'_filtered_'+str(number)
	try:
		createTable(table)
	except:
		conn.rollback()
		cursor.execute("Truncate "+ table+";")
		conn.commit()
		print "Table Already Exists!! \nContinuing with Execution..."
	query = "SELECT DISTINCT text_id FROM %s;" %(originalTable)
	cursor.execute(query)
	conn.commit()
	results = cursor.fetchall()

	for index,result in enumerate(results):
		print "Filtering "+ str("{0:.2f}".format(index/len(results) * 100)) + '%'
		text_id = result[0]
		keywords = fetchCandidateKeywords(originalTable,text_id)
		phrase_list = getAllPhrases(getText(text_id))
		sorted_keywords = sortAccordingToScore(keywords,phrase_list)
		writeToTable(table,sorted_keywords[:number],text_id)
	

if __name__=='__main__':
	args = sys.argv
	if len(args) > 1:
		if(args[1] == '-n'):
			start_naive_bayes_tagging('krapivin_naivebayes_classifier_result_tags')
		elif (args[1] == '-svm'):
			n = args[2]
			if (int(n) and n > 0):
				for i in range(5,15+1):
					start_svm_tagging('hulth_svm_classifier_result_tags',i)
			# start_svm_tagging('krapivin_svm_classifier_result_tags',int(n))
			else:
				print n, isinstance( n, int ), n>0
		else:
			print "Usage: python run_classifier -flag number" \
			"\n\tflag = -n to run naivebayes classifier and generate n words per tag" \
			"\n\tflag = -svm to run svm classifier and generate n words per tag" \
			"\n\tnumber > 0"
			exit(1)
	else:
		print "Usage: python run_classifier -flag" \
		"\n\tflag = -n to run naivebayes classifier and generate n words per tag" \
		"\n\tflag = -svm to run svm classifier and generate n words per tag" \
		"\n\tnumber > 0"
		exit(1)