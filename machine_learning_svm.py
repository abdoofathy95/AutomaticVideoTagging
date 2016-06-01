from __future__ import division
from sklearn import svm
import psycopg2
import pickle
import machine_learning_naivebayes as mln
from sklearn.feature_extraction import DictVectorizer
from pysofia.compat import RankSVM

def is_tag(word,tags): 
	'''
	Utility Function: returns 0 (not a tag) or 1 (TAG)
	'''
	for tag in tags:
		list = tag.split(' ')
		list = map(mln.stem,list)
		if word.stem in list:
			return 1
	return 0

if __name__ == '__main__':
	# Open Connection To Database
	conn = psycopg2.connect("dbname=datasets user=abdoo") # connect to database
	cursor = conn.cursor() # connect to database
	query = "SELECT id,title,text FROM hulth WHERE id <= 1000;"
	query2 = "SELECT text_id,tag FROM hulth_tags;"
	cursor.execute(query)
	conn.commit()
	results = cursor.fetchall()
	train_set = results
	feature_train_set = []
	class_labels = []
	cursor.execute(query2)
	conn.commit()
	all_tags = cursor.fetchall()
 	for result_index,result in enumerate(train_set): 
		print "Progress: "+ str("{0:.2f}".format(result_index/len(train_set) * 100)) + '%'
		abstractId = int(result[0])
		title = str(result[1])
		text = str(result[2])
		abstract = mln.preprocess(text)
		tags = mln.getTags(abstractId,all_tags)
		maximal = mln.getMaxScore(abstract)
		for word_index,word in enumerate(abstract):
			prev_word = abstract[word_index-1] if word_index-1 >= 0 else mln.Word('')
			next_word = abstract[word_index+1] if word_index+1 < len(abstract) else mln.Word('')
			second_prev_word = abstract[word_index-2] if word_index-2 >= 0 else mln.Word('')
			second_next_word = abstract[word_index+2] if word_index+2 < len(abstract) else mln.Word('')
			feature_train_set.append(
				(mln.extract_features(abstractId,text,abstract,title,maximal,word,word_index,prev_word,next_word,second_prev_word,second_next_word)))
			class_labels.append(is_tag(word,tags)) 

	vectorizer = DictVectorizer()
	X=vectorizer.fit_transform(feature_train_set)
	# classifier = svm.SVC()
	# classifier.fit(X,class_labels)
	classifier = RankSVM().fit(X, class_labels)
	print 'Writing the vectorizer to Disk...'
	pickle.dump(vectorizer,open( "svm_vectorizer.vectorizer", "wb" ))
	print 'Writing the classifier to Disk...'
	pickle.dump(classifier,open( "svm_classifier.cls", "wb" ))
