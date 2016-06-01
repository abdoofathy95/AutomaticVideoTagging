from __future__ import division
import psycopg2
from difflib import SequenceMatcher
import collections
from nltk.stem import PorterStemmer
import sys

# Open Connection To Database
conn = psycopg2.connect("dbname=datasets user=abdoo") # connect to database
cursor = conn.cursor() # connect to database

def score(tag1,tag2): 	# find a ratio representing the similarity between two tags
	'''
	Score is calculated on two steps
		1) filteration: calculate the freq_score = sum (freq of each string in tag1/number of strings in tag2)
		2) using a string similarity algorithm to get sim_score
	so score = freq_score*sim_score
	@params (tag1): string of words seperated by spaces
	@params (tag2): string of words seperated by spaces
	@returns (float): representing the similarity
	'''
	match = SequenceMatcher(None)
	tag1_list = tag1.split(' ')
	tag2_list = tag2.split(' ')
	freq_score = 0
	for str1 in tag1_list :
		freq = 0
		for str2 in tag2_list:
			if str1 == str2 :
				freq += 1
		freq_score += freq
	freq_score /= len(tag2_list)
	match.set_seq1(tag1)
	match.set_seq2(tag2)
	sim_score = match.ratio()
	return freq_score * sim_score

def createQuery(name1,name2,limit=False):
	if(limit):
		query = 'SELECT '+ name2 + '.text_id,' + name2 +'.tag,'''+name1+'''.tag FROM 
			'''+name2+''' INNER JOIN '''+name1+''' ON 
			('''+name2+'.text_id = '''+name1+'.text_id) WHERE '+name1+'''.text_id > 1000
			GROUP BY ''' + name2 +'.text_id,' + name2+'.tag,'''+name1+'''.tag;'''
		query2 = "SELECT * FROM "+name1+" WHERE text_id > 1000;"
	else:
		query = 'SELECT '+ name2 + '.text_id,' + name2 +'.tag,'''+name1+'''.tag FROM 
			'''+name2+' INNER JOIN '+name1+''' ON 
			('''+name2+'.text_id = '+name1+'''.text_id)
			GROUP BY ''' + name2 +'.text_id,' + name2+'.tag,'''+name1+'''.tag;'''
		query2 = "SELECT * FROM "+name1+";"
	return (query,query2)

correctTagsMatched = collections.defaultdict(list)
resultTagsMatched = collections.defaultdict(list)
tempTagsMatched = collections.defaultdict(list)
def correctTagAlreadyCounted(id , tag):
	return tag in correctTagsMatched[id]

def resultTagAlreadyCounted(id , tag):
	return tag in resultTagsMatched[id]

def tempTagAlreadyCounted(id , tag):
	return tag in tempTagsMatched[id]

def addToCorrectTagsCounted(id , tag):	
	correctTagsMatched[id].append(tag)

def addToResultTagsCounted(id , tag):	
	resultTagsMatched[id].append(tag)

def addToTempTagsCounted(id , tag):	
	tempTagsMatched[id].append(tag)

stemmer = PorterStemmer()
def isTagFound(tag,other_tag):
	'''
	@params tag: string of single word (not stemmed word)
	@params list: string of multiple words (also not stemmed)
	@returns boolean : depends on defined criteria below
	Current Criteria : TAG EXIST IN THE Other Tag as a Substring (Stem of the word) --> TO BE CHANGED LATER
	'''
	list = other_tag.split(' ')
	list = map(stemmer.stem,list)
	tag = stemmer.stem(tag)
	if tag in list:
		return True
	return False

def rake_all_tags_compare():
	databases = {}
	for i in range(5,15+1):
		resultTagsMatched.clear()
		correctTagsMatched.clear()
		query1 = "SELECT * FROM hulth_tags WHERE text_id>1000;"
		queries = createQuery('hulth_result_tags_rake_'+str(i),'hulth_tags',limit=True)
		query = queries[0]
		query2 = queries[1]
		databases['hulth_result_tags_rake_'+str(i)] = {}
		cursor.execute(query)
		conn.commit()
		results = cursor.fetchall()
		TP = 0	# True Positive (relevant items that we correctly identified as relevant)
		FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
		FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
		for result in results:
			textId = int(result[0])
			correct_tag = str(result[1]).lower()
			result_tag = str(result[2]).lower()
			for string in result_tag.split(' '):
				if(isTagFound(string,correct_tag)):
					if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
						TP += 1
						addToResultTagsCounted(textId,result_tag)
						addToCorrectTagsCounted(textId,correct_tag)

		# GET Total Number Of Correct Tags and Total Number Of Result Tags
		cursor.execute(query1)
		conn.commit()
		correct_tags_count = len(cursor.fetchall())
		cursor.execute(query2)
		conn.commit()
		result_tags_count = len(cursor.fetchall())
		# FN is Total Number Of Correct Tags - TP
		FN = correct_tags_count - TP
		# FP is Total Number Of Result Tags - TP	
		FP = result_tags_count - TP
		# Percision is TP/(TP+FP)
		precision = TP/(TP+FP)
		# Recall is TP/(TP+FN)
		recall = TP/(TP+FN)
		# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
		databases['hulth_result_tags_rake_'+str(i)]['TP'] = TP
		databases['hulth_result_tags_rake_'+str(i)]['FN'] = FN
		databases['hulth_result_tags_rake_'+str(i)]['FP'] = FP
		databases['hulth_result_tags_rake_'+str(i)]['Precision'] = precision
		databases['hulth_result_tags_rake_'+str(i)]['Recall'] = recall
		try:
			fScore = (2*precision*recall)/(precision+recall)
			databases['hulth_result_tags_rake_'+str(i)]['FScore'] = fScore
		except:
			print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
			exit(0)
		print 'hulth_result_tags_rake_'+str(i)
		print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
		print "True Positive :"+ str(TP)
		print "False Negative :"+ str(FN)
		print "False Positive :"+ str(FP)
		print "Precision :"+ str("%.3f"%(precision*100))+'%'
		print "Recall :"+ str("%.3f"%(recall*100))+'%'
		print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

	print "Highest TP : " + sorted(databases,key=lambda x: databases[x]['TP'],reverse=True)[0]
	print "Highest FN : " + sorted(databases,key=lambda x: databases[x]['FN'],reverse=True)[0]
	print "Highest FP : " + sorted(databases,key=lambda x: databases[x]['FP'],reverse=True)[0]
	print "Highest Precision : " + sorted(databases,key=lambda x: databases[x]['Precision'],reverse=True)[0]
	print "Highest Recall : " + sorted(databases,key=lambda x: databases[x]['Recall'],reverse=True)[0]
	print "Highest FScore : " + sorted(databases,key=lambda x: databases[x]['FScore'],reverse=True)[0]
	print "***********************************************"
	print "***********************************************"
def rake_word_matching():
	query = '''SELECT hulth_tags.text_id,hulth_tags.tag,hulth_result_tags_rake_6.tag FROM 
		hulth_tags INNER JOIN hulth_result_tags_rake_6 ON 
		(hulth_tags.text_id = hulth_result_tags_rake_6.text_id) and hulth_tags.text_id > 1000
		GROUP BY hulth_tags.text_id,hulth_tags.tag,hulth_result_tags_rake_6.tag;''' 
	# query = '''SELECT krapivin_tags.text_id,krapivin_tags.tag,krapivin_text_result_tags_rake_10.tag FROM 
	# 	krapivin_tags INNER JOIN krapivin_text_result_tags_rake_10 ON 
	# 	(krapivin_tags.text_id = krapivin_text_result_tags_rake_10.text_id)
	# 	GROUP BY krapivin_tags.text_id,krapivin_tags.tag,krapivin_text_result_tags_rake_10.tag;''' 
	cursor.execute(query)
	conn.commit()

	results = cursor.fetchall()
	TP = 0	# True Positive (relevant items that we correctly identified as relevant)
	FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
	FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
	correct_tags_count = 0 # counting in words
	result_tags_count = 0
	for result in results:
		textId = result[0]
		correct_tag = str(result[1]).lower()
		result_tag = str(result[2]).lower()
		correct_list = map(stemmer.stem,correct_tag.split(' '))
		result_list = map(stemmer.stem,result_tag.split(' '))

		if not correctTagAlreadyCounted(textId,correct_tag):
			correct_tags_count += len(correct_list) # add length (number of correct words)
			addToCorrectTagsCounted(textId,correct_tag)
		if not resultTagAlreadyCounted(textId,result_tag):
			result_tags_count += len(result_list)
			addToResultTagsCounted(textId,result_tag)
		for tag in result_list:
			if tag in correct_list:
				if not tempTagAlreadyCounted(textId,tag):
					TP += 1
					addToTempTagsCounted(textId,tag)
	# FN is Total Number Of Correct Tags - TP
	FN = correct_tags_count - TP
	# FP is Total Number Of Result Tags - TP	
	FP = result_tags_count - TP
	# Percision is TP/(TP+FP)
	precision = TP/(TP+FP)
	# Recall is TP/(TP+FN)
	recall = TP/(TP+FN)
	# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
	try:
		fScore = (2*precision*recall)/(precision+recall)
	except:
		print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
		exit(0)
	print "CORRECT WORDS COUNT :"+ str(correct_tags_count)
	print "RESULT WORDS COUNT :"+ str(result_tags_count)
	print "True Positive :"+ str(TP)
	print "False Negative :"+ str(FN)
	print "False Positive :"+ str(FP)
	print "Precision :"+ str("%.3f"%(precision*100))+'%'
	print "Recall :"+ str("%.3f"%(recall*100))+'%'
	print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

def naive_bayes_word_matching():
	query = '''SELECT hulth_tags.text_id,hulth_tags.tag,hulth_word_classifier_result_tags.tag FROM 
	hulth_tags INNER JOIN hulth_word_classifier_result_tags ON 
	(hulth_tags.text_id = hulth_word_classifier_result_tags.text_id) and hulth_tags.text_id > 1000
	GROUP BY hulth_tags.text_id,hulth_tags.tag,hulth_word_classifier_result_tags.tag;''' 
	query1 = "SELECT * FROM hulth_word_classifier_result_tags;"
	query2 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
	cursor.execute(query)
	conn.commit()
	results = cursor.fetchall()
	TP = 0	# True Positive (relevant items that we correctly identified as relevant)
	FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
	FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)

	for result in results:
		textId = result[0]
		correct_tag = str(result[1]).lower()
		list = map(stemmer.stem,correct_tag.split(' '))
		result_tag = stemmer.stem(str(result[2]).lower())
		
		if result_tag in list:
			if not resultTagAlreadyCounted(textId,result_tag):
				TP += 1
				addToResultTagsCounted(textId,result_tag)

	cursor.execute(query1)
	conn.commit()
	result_tags_count = len(cursor.fetchall())
	cursor.execute(query2)
	conn.commit()
	re = cursor.fetchall()
	correct_tags_count = 0 # counting in words
	for r in re:
		correct_tags_count+= len(r[2].split(' '))
	# FN is Total Number Of Correct Tags - TP
	FN = correct_tags_count - TP
	# FP is Total Number Of Result Tags - TP	
	FP = result_tags_count - TP
	# Percision is TP/(TP+FP)
	precision = TP/(TP+FP)
	# Recall is TP/(TP+FN)
	recall = TP/(TP+FN)
	try:
		fScore = (2*precision*recall)/(precision+recall)
	except:
		print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
		exit(0)
	print "CORRECT WORDS COUNT :"+ str(correct_tags_count)
	print "RESULT WORDS COUNT :"+ str(result_tags_count)
	print "True Positive :"+ str(TP)
	print "False Negative :"+ str(FN)
	print "False Positive :"+ str(FP)
	print "Precision :"+ str("%.3f"%(precision*100))+'%'
	print "Recall :"+ str("%.3f"%(recall*100))+'%'
	print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

def rake_tag_matching():
	# query = '''SELECT hulth_tags.text_id,hulth_tags.tag,hulth_result_tags_rake_6.tag FROM 
	# hulth_tags INNER JOIN hulth_result_tags_rake_6 ON 
	# (hulth_tags.text_id = hulth_result_tags_rake_6.text_id) and hulth_tags.text_id > 1000
	# GROUP BY hulth_tags.text_id,hulth_tags.tag,hulth_result_tags_rake_6.tag;''' 
	query = '''SELECT krapivin_tags.text_id,krapivin_tags.tag,krapivin_text_result_tags_rake_5.tag FROM 
		krapivin_tags INNER JOIN krapivin_text_result_tags_rake_5 ON 
		(krapivin_tags.text_id = krapivin_text_result_tags_rake_5.text_id)
		GROUP BY krapivin_tags.text_id,krapivin_tags.tag,krapivin_text_result_tags_rake_5.tag;''' 
	# query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
	# query2 = "SELECT * FROM hulth_result_tags_rake_6 WHERE text_id > 1000;"
	query1 = "SELECT * FROM krapivin_tags;"
	query2 = "SELECT * FROM krapivin_text_result_tags_rake_5;"
	cursor.execute(query)
	conn.commit()

	results = cursor.fetchall()
	TP = 0	# True Positive (relevant items that we correctly identified as relevant)
	FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
	FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
	for result in results:
		textId = int(result[0])
		correct_tag = str(result[1]).lower()
		result_tag = str(result[2]).lower()
		for string in result_tag.split(' '):
			if(isTagFound(string,correct_tag)):
				if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
					TP += 1
					addToResultTagsCounted(textId,result_tag)
					addToCorrectTagsCounted(textId,correct_tag)
		
	# GET Total Number Of Correct Tags and Total Number Of Result Tags
	cursor.execute(query1)
	conn.commit()
	correct_tags_count = len(cursor.fetchall())
	cursor.execute(query2)
	conn.commit()
	result_tags_count = len(cursor.fetchall())
	# FN is Total Number Of Correct Tags - TP
	FN = correct_tags_count - TP
	# FP is Total Number Of Result Tags - TP	
	FP = result_tags_count - TP
	# Percision is TP/(TP+FP)
	precision = TP/(TP+FP)
	# Recall is TP/(TP+FN)
	recall = TP/(TP+FN)
	# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
	try:
		fScore = (2*precision*recall)/(precision+recall)
	except:
		print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
		exit(0)

	print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
	print "RESULT TAGS COUNT :"+ str(result_tags_count)
	print "True Positive :"+ str(TP)
	print "False Negative :"+ str(FN)
	print "False Positive :"+ str(FP)
	print "Precision :"+ str("%.3f"%(precision*100))+'%'
	print "Recall :"+ str("%.3f"%(recall*100))+'%'
	print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

def naive_bayes_tag_matching():
	# queries = createQuery('hulth_classifier_result_tags_filtered','hulth_tags')
	queries = createQuery('krapivin_classifier_result_tags_filtered_6','krapivin_tags')
	query = queries[0]
	# query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
	# query2 = "SELECT * FROM hulth_classifier_result_tags_filtered;"
	query1 = "SELECT * FROM krapivin_tags"
	query2 = "SELECT * FROM krapivin_classifier_result_tags_filtered_6;"
	cursor.execute(query)
	conn.commit()

	results = cursor.fetchall()
	TP = 0	# True Positive (relevant items that we correctly identified as relevant)
	FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
	FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
	for result in results:
		textId = int(result[0])
		correct_tag = str(result[1]).lower()
		result_tag = str(result[2]).lower()
		for string in result_tag.split(' '):
			if(isTagFound(string,correct_tag)):
				if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
					TP += 1
					addToResultTagsCounted(textId,result_tag)
					addToCorrectTagsCounted(textId,correct_tag)
		
	# GET Total Number Of Correct Tags and Total Number Of Result Tags
	cursor.execute(query1)
	conn.commit()
	correct_tags_count = len(cursor.fetchall())
	cursor.execute(query2)
	conn.commit()
	result_tags_count = len(cursor.fetchall())
	# FN is Total Number Of Correct Tags - TP
	FN = correct_tags_count - TP
	# FP is Total Number Of Result Tags - TP	
	FP = result_tags_count - TP
	# Percision is TP/(TP+FP)
	precision = TP/(TP+FP)
	# Recall is TP/(TP+FN)
	recall = TP/(TP+FN)
	# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
	try:
		fScore = (2*precision*recall)/(precision+recall)
	except:
		print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
		exit(0)

	print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
	print "RESULT TAGS COUNT :"+ str(result_tags_count)
	print "True Positive :"+ str(TP)
	print "False Negative :"+ str(FN)
	print "False Positive :"+ str(FP)
	print "Precision :"+ str("%.3f"%(precision*100))+'%'
	print "Recall :"+ str("%.3f"%(recall*100))+'%'
	print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

def naive_bayes_all_tags_compare():
	databases = {}
	for i in range(5,15+1):
		resultTagsMatched.clear()
		correctTagsMatched.clear()
		query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
		queries = createQuery('hulth_classifier_result_tags_filtered_'+str(i),'hulth_tags',limit=True)
		query = queries[0]
		query2 = queries[1]
		databases['hulth_classifier_result_tags_filtered_'+str(i)] = {}
		cursor.execute(query)
		conn.commit()
		results = cursor.fetchall()
		TP = 0	# True Positive (relevant items that we correctly identified as relevant)
		FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
		FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
		for result in results:
			textId = int(result[0])
			correct_tag = str(result[1]).lower()
			result_tag = str(result[2]).lower()
			for string in result_tag.split(' '):
				if(isTagFound(string,correct_tag)):
					if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
						TP += 1
						addToResultTagsCounted(textId,result_tag)
						addToCorrectTagsCounted(textId,correct_tag)

		# GET Total Number Of Correct Tags and Total Number Of Result Tags
		cursor.execute(query1)
		conn.commit()
		correct_tags_count = len(cursor.fetchall())
		cursor.execute(query2)
		conn.commit()
		result_tags_count = len(cursor.fetchall())
		# FN is Total Number Of Correct Tags - TP
		FN = correct_tags_count - TP
		# FP is Total Number Of Result Tags - TP	
		FP = result_tags_count - TP
		# Percision is TP/(TP+FP)
		precision = TP/(TP+FP)
		# Recall is TP/(TP+FN)
		recall = TP/(TP+FN)
		# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
		databases['hulth_classifier_result_tags_filtered_'+str(i)]['TP'] = TP
		databases['hulth_classifier_result_tags_filtered_'+str(i)]['FN'] = FN
		databases['hulth_classifier_result_tags_filtered_'+str(i)]['FP'] = FP
		databases['hulth_classifier_result_tags_filtered_'+str(i)]['Precision'] = precision
		databases['hulth_classifier_result_tags_filtered_'+str(i)]['Recall'] = recall
		try:
			fScore = (2*precision*recall)/(precision+recall)
			databases['hulth_classifier_result_tags_filtered_'+str(i)]['FScore'] = fScore
		except:
			print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
			exit(0)
		print 'hulth_classifier_result_tags_filtered_'+str(i)
		print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
		print "True Positive :"+ str(TP)
		print "False Negative :"+ str(FN)
		print "False Positive :"+ str(FP)
		print "Precision :"+ str("%.3f"%(precision*100))+'%'
		print "Recall :"+ str("%.3f"%(recall*100))+'%'
		print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

	print "Highest TP : " + sorted(databases,key=lambda x: databases[x]['TP'],reverse=True)[0]
	print "Highest FN : " + sorted(databases,key=lambda x: databases[x]['FN'],reverse=True)[0]
	print "Highest FP : " + sorted(databases,key=lambda x: databases[x]['FP'],reverse=True)[0]
	print "Highest Precision : " + sorted(databases,key=lambda x: databases[x]['Precision'],reverse=True)[0]
	print "Highest Recall : " + sorted(databases,key=lambda x: databases[x]['Recall'],reverse=True)[0]
	print "Highest FScore : " + sorted(databases,key=lambda x: databases[x]['FScore'],reverse=True)[0]
	print "***********************************************"
	print "***********************************************"

def rank_svm_tag_matching():
	# queries = createQuery('hulth_classifier_result_tags_filtered','hulth_tags')
	# queries = createQuery('krapivin_classifier_result_tags_filtered_6','krapivin_tags')
	query = queries[0]
	# query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
	# query2 = "SELECT * FROM hulth_classifier_result_tags_filtered;"
	query1 = "SELECT * FROM krapivin_tags"
	query2 = "SELECT * FROM krapivin_classifier_result_tags_filtered_6;"
	cursor.execute(query)
	conn.commit()

	results = cursor.fetchall()
	TP = 0	# True Positive (relevant items that we correctly identified as relevant)
	FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
	FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
	for result in results:
		textId = int(result[0])
		correct_tag = str(result[1]).lower()
		result_tag = str(result[2]).lower()
		for string in result_tag.split(' '):
			if(isTagFound(string,correct_tag)):
				if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
					TP += 1
					addToResultTagsCounted(textId,result_tag)
					addToCorrectTagsCounted(textId,correct_tag)
		
	# GET Total Number Of Correct Tags and Total Number Of Result Tags
	cursor.execute(query1)
	conn.commit()
	correct_tags_count = len(cursor.fetchall())
	cursor.execute(query2)
	conn.commit()
	result_tags_count = len(cursor.fetchall())
	# FN is Total Number Of Correct Tags - TP
	FN = correct_tags_count - TP
	# FP is Total Number Of Result Tags - TP	
	FP = result_tags_count - TP
	# Percision is TP/(TP+FP)
	precision = TP/(TP+FP)
	# Recall is TP/(TP+FN)
	recall = TP/(TP+FN)
	# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
	try:
		fScore = (2*precision*recall)/(precision+recall)
	except:
		print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
		exit(0)

	print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
	print "RESULT TAGS COUNT :"+ str(result_tags_count)
	print "True Positive :"+ str(TP)
	print "False Negative :"+ str(FN)
	print "False Positive :"+ str(FP)
	print "Precision :"+ str("%.3f"%(precision*100))+'%'
	print "Recall :"+ str("%.3f"%(recall*100))+'%'
	print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

def rank_svm_all_tags_compare():
	databases = {}
	for i in range(5,15+1):
		resultTagsMatched.clear()
		correctTagsMatched.clear()
		query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
		queries = createQuery('hulth_svm_classifier_result_tags_'+str(i),'hulth_tags',limit=True)
		query = queries[0]
		query2 = queries[1]
		databases['hulth_svm_classifier_result_tags_'+str(i)] = {}
		cursor.execute(query)
		conn.commit()
		results = cursor.fetchall()
		TP = 0	# True Positive (relevant items that we correctly identified as relevant)
		FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
		FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
		for result in results:
			textId = int(result[0])
			correct_tag = str(result[1]).lower()
			result_tag = str(result[2]).lower()
			for string in result_tag.split(' '):
				if(isTagFound(string,correct_tag)):
					if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
						TP += 1
						addToResultTagsCounted(textId,result_tag)
						addToCorrectTagsCounted(textId,correct_tag)

		# GET Total Number Of Correct Tags and Total Number Of Result Tags
		cursor.execute(query1)
		conn.commit()
		correct_tags_count = len(cursor.fetchall())
		cursor.execute(query2)
		conn.commit()
		result_tags_count = len(cursor.fetchall())
		# FN is Total Number Of Correct Tags - TP
		FN = correct_tags_count - TP
		# FP is Total Number Of Result Tags - TP	
		FP = result_tags_count - TP
		# Percision is TP/(TP+FP)
		precision = TP/(TP+FP)
		# Recall is TP/(TP+FN)
		recall = TP/(TP+FN)
		# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
		databases['hulth_svm_classifier_result_tags_'+str(i)]['TP'] = TP
		databases['hulth_svm_classifier_result_tags_'+str(i)]['FN'] = FN
		databases['hulth_svm_classifier_result_tags_'+str(i)]['FP'] = FP
		databases['hulth_svm_classifier_result_tags_'+str(i)]['Precision'] = precision
		databases['hulth_svm_classifier_result_tags_'+str(i)]['Recall'] = recall
		try:
			fScore = (2*precision*recall)/(precision+recall)
			databases['hulth_svm_classifier_result_tags_'+str(i)]['FScore'] = fScore
		except:
			print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
			exit(0)
		print 'hulth_svm_classifier_result_tags_'+str(i)
		print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
		print "True Positive :"+ str(TP)
		print "False Negative :"+ str(FN)
		print "False Positive :"+ str(FP)
		print "Precision :"+ str("%.3f"%(precision*100))+'%'
		print "Recall :"+ str("%.3f"%(recall*100))+'%'
		print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

	print "Highest TP : " + sorted(databases,key=lambda x: databases[x]['TP'],reverse=True)[0]
	print "Highest FN : " + sorted(databases,key=lambda x: databases[x]['FN'],reverse=True)[0]
	print "Highest FP : " + sorted(databases,key=lambda x: databases[x]['FP'],reverse=True)[0]
	print "Highest Precision : " + sorted(databases,key=lambda x: databases[x]['Precision'],reverse=True)[0]
	print "Highest Recall : " + sorted(databases,key=lambda x: databases[x]['Recall'],reverse=True)[0]
	print "Highest FScore : " + sorted(databases,key=lambda x: databases[x]['FScore'],reverse=True)[0]
	print "***********************************************"
	print "***********************************************"

def tagger_all_tags_compare():
	databases = {}
	for i in range(5,15+1):
		resultTagsMatched.clear()
		correctTagsMatched.clear()
		query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
		queries = createQuery('hulth_result_tags_tagger_'+str(i),'hulth_tags',limit=True)
		query = queries[0]
		query2 = queries[1]
		databases['hulth_result_tags_tagger_'+str(i)] = {}
		cursor.execute(query)
		conn.commit()
		results = cursor.fetchall()
		TP = 0	# True Positive (relevant items that we correctly identified as relevant)
		FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
		FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
		for result in results:
			textId = int(result[0])
			correct_tag = str(result[1]).lower()
			result_tag = str(result[2]).lower()
			for string in result_tag.split(' '):
				if(isTagFound(string,correct_tag)):
					if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
						TP += 1
						addToResultTagsCounted(textId,result_tag)
						addToCorrectTagsCounted(textId,correct_tag)

		# GET Total Number Of Correct Tags and Total Number Of Result Tags
		cursor.execute(query1)
		conn.commit()
		correct_tags_count = len(cursor.fetchall())
		cursor.execute(query2)
		conn.commit()
		result_tags_count = len(cursor.fetchall())
		# FN is Total Number Of Correct Tags - TP
		FN = correct_tags_count - TP
		# FP is Total Number Of Result Tags - TP	
		FP = result_tags_count - TP
		# Percision is TP/(TP+FP)
		precision = TP/(TP+FP)
		# Recall is TP/(TP+FN)
		recall = TP/(TP+FN)
		# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
		databases['hulth_result_tags_tagger_'+str(i)]['TP'] = TP
		databases['hulth_result_tags_tagger_'+str(i)]['FN'] = FN
		databases['hulth_result_tags_tagger_'+str(i)]['FP'] = FP
		databases['hulth_result_tags_tagger_'+str(i)]['Precision'] = precision
		databases['hulth_result_tags_tagger_'+str(i)]['Recall'] = recall
		try:
			fScore = (2*precision*recall)/(precision+recall)
			databases['hulth_result_tags_tagger_'+str(i)]['FScore'] = fScore
		except:
			print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
			exit(0)
		print 'hulth_result_tags_tagger_'+str(i)
		print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
		print "True Positive :"+ str(TP)
		print "False Negative :"+ str(FN)
		print "False Positive :"+ str(FP)
		print "Precision :"+ str("%.3f"%(precision*100))+'%'
		print "Recall :"+ str("%.3f"%(recall*100))+'%'
		print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'

	print "Highest TP : " + sorted(databases,key=lambda x: databases[x]['TP'],reverse=True)[0]
	print "Highest FN : " + sorted(databases,key=lambda x: databases[x]['FN'],reverse=True)[0]
	print "Highest FP : " + sorted(databases,key=lambda x: databases[x]['FP'],reverse=True)[0]
	print "Highest Precision : " + sorted(databases,key=lambda x: databases[x]['Precision'],reverse=True)[0]
	print "Highest Recall : " + sorted(databases,key=lambda x: databases[x]['Recall'],reverse=True)[0]
	print "Highest FScore : " + sorted(databases,key=lambda x: databases[x]['FScore'],reverse=True)[0]
	print "***********************************************"
	print "***********************************************"

def tagger_tag_matching():
	# query = '''SELECT hulth_tags.text_id,hulth_tags.tag,hulth_result_tags_rake_6.tag FROM 
	# hulth_tags INNER JOIN hulth_result_tags_rake_6 ON 
	# (hulth_tags.text_id = hulth_result_tags_rake_6.text_id) and hulth_tags.text_id > 1000
	# GROUP BY hulth_tags.text_id,hulth_tags.tag,hulth_result_tags_rake_6.tag;''' 
	query = '''SELECT krapivin_tags.text_id,krapivin_tags.tag,krapivin_text_result_tags_tagger_8.tag FROM 
		krapivin_tags INNER JOIN krapivin_text_result_tags_tagger_8 ON 
		(krapivin_tags.text_id = krapivin_text_result_tags_tagger_8.text_id)
		GROUP BY krapivin_tags.text_id,krapivin_tags.tag,krapivin_text_result_tags_tagger_8.tag;''' 
	# query1 = "SELECT * FROM hulth_tags WHERE text_id > 1000;"
	# query2 = "SELECT * FROM hulth_result_tags_rake_6 WHERE text_id > 1000;"
	query1 = "SELECT * FROM krapivin_tags;"
	query2 = "SELECT * FROM krapivin_text_result_tags_tagger_8;"
	cursor.execute(query)
	conn.commit()

	results = cursor.fetchall()
	TP = 0	# True Positive (relevant items that we correctly identified as relevant)
	FN = 0  # False Negative (relevant items that we incorrectly identified as irrelevant)
	FP = 0	# False Positive (irrelevant items that we incorrectly identified as relevant)
		
	for result in results:
		textId = int(result[0])
		correct_tag = str(result[1]).lower()
		result_tag = str(result[2]).lower()
		for string in result_tag.split(' '):
			if(isTagFound(string,correct_tag)):
				if not (resultTagAlreadyCounted(textId, result_tag)) and not (correctTagAlreadyCounted(textId,correct_tag)): # discard the tag if already counted as TP
					TP += 1
					addToResultTagsCounted(textId,result_tag)
					addToCorrectTagsCounted(textId,correct_tag)
		
	# GET Total Number Of Correct Tags and Total Number Of Result Tags
	cursor.execute(query1)
	conn.commit()
	correct_tags_count = len(cursor.fetchall())
	cursor.execute(query2)
	conn.commit()
	result_tags_count = len(cursor.fetchall())
	# FN is Total Number Of Correct Tags - TP
	FN = correct_tags_count - TP
	# FP is Total Number Of Result Tags - TP	
	FP = result_tags_count - TP
	# Percision is TP/(TP+FP)
	precision = TP/(TP+FP)
	# Recall is TP/(TP+FN)
	recall = TP/(TP+FN)
	# F-Measure (F-Score) is (2 * Precision * Recall) / (Precision + Recall)
	try:
		fScore = (2*precision*recall)/(precision+recall)
	except:
		print "FScore Result Unknown Can't Divide By 0, precision + recall = 0"
		exit(0)

	print "CORRECT TAGS COUNT :"+ str(correct_tags_count)
	print "RESULT TAGS COUNT :"+ str(result_tags_count)
	print "True Positive :"+ str(TP)
	print "False Negative :"+ str(FN)
	print "False Positive :"+ str(FP)
	print "Precision :"+ str("%.3f"%(precision*100))+'%'
	print "Recall :"+ str("%.3f"%(recall*100))+'%'
	print "F-Measure(F-Score) :"+ str("%.3f"%(fScore*100))+'%'


if __name__ == "__main__":
	args = sys.argv
	if len(args) > 1:
		if(args[1] == '-ra'):
			rake_all_tags_compare()
		elif (args[1] == '-mw'):
			naive_bayes_word_matching()
		elif (args[1] == '-rw'):
			rake_word_matching()
		elif (args[1] == '-m'):
			naive_bayes_tag_matching()
		elif (args[1] == '-r'):
			rake_tag_matching()
		elif (args[1] == '-ta'):
			tagger_all_tags_compare()
		elif (args[1] == '-t'):
			tagger_tag_matching()
		elif (args[1] == '-ma'):
			naive_bayes_all_tags_compare()
		elif (args[1] == '-svma'):
			rank_svm_all_tags_compare()
		elif (args[1] == '-svm'):
			rank_svm_tag_matching()
		else:
			print "Usage: python measureAccuracy -flag" \
			"\n\tflag = -ra to run comparison between tag sizes with accuracy measurements on RAKE" \
			"\n\tflag = -ma to run comparison between tag sizes with accuracy measurements on naive bayes" \
			"\n\tflag = -svma to run comparison between tag sizes with accuracy measurements on rank svm" \
			"\n\tflag = -ta to run comparison between tag sizes with accuracy measurements on tagger" \
			"\n\tflag = -m to run test on best # of tags on naive bayes" \
			"\n\tflag = -svm to run test on best # of tags on rank svm" \
			"\n\tflag = -r to run test on best # of tags on RAKE" \
			"\n\tflag = -t to run test on best # of tags on tagger" 
			exit(1)
	else:
		print "Usage: python measureAccuracy -flag" \
		"\n\tflag = -ra to run comparison between tag sizes with accuracy measurements on RAKE" \
			"\n\tflag = -ma to run comparison between tag sizes with accuracy measurements on naive bayes" \
			"\n\tflag = -svma to run comparison between tag sizes with accuracy measurements on rank svm" \
			"\n\tflag = -ta to run comparison between tag sizes with accuracy measurements on tagger" \
			"\n\tflag = -m to run test on best # of tags on naive bayes" \
			"\n\tflag = -svm to run test on best # of tags on rank svm" \
			"\n\tflag = -r to run test on best # of tags on RAKE" \
			"\n\tflag = -t to run test on best # of tags on tagger" 
		exit(1)