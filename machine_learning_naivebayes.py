# -*- coding: utf-8 -*-
from __future__ import division
import nltk
import psycopg2
import pickle
from nltk.stem import PorterStemmer
from nltk import word_tokenize
from nltk.tag.perceptron import PerceptronTagger
from rake import rake
import collections
import re
import unicodedata

'''
idea : construct feature set by applying extract_features function to a dataset
	   then splitting this feature set to three sets (train_set,dev_set,test_set)
	   train_set: used for trainning the classifier (currenly NaiveBayesClassifier)
	   dev_set: used for initial test and optimization of features
	   test_set: used for final testing to measure accuracy
'''
dict = pickle.load(open('scientific_dict.pkl')) # dictionary of IDF built from 5000 nytimes articles (TO BE CHANGED INTO a SCIENTIFIC DICT)
stemmer = PorterStemmer()
pos_tagger = PerceptronTagger()

class Word:
    
    def __init__(self, string, stem=None):
        '''
        @param string:   the actual representation of the word
        @param stem:     the internal (usually stemmed) representation;
        @returns: a new L{Word} object
        '''
            
        self.string  = string
        self.stem = stem or string

def stem(string):
	''' Utility Method
	@params string: string to be stemmed (one word or n-words split by hyphen)
	@return stem of a string
	'''
	match_contractions = re.compile(r'(\w+)\'(m|re|d|ve|s|ll|t)?')
	match_hyphens = re.compile(r'\b[\-_]\b')
	
	string = match_hyphens.sub('', string)
	match = match_contractions.match(string)
	if match: string = match.group(1)
	return unicodedata.normalize('NFKD', stemmer.stem(string)).encode('ascii','ignore') # return a string not a uni

def get_score(word,text):
	word_freq = calculate_freq(word,text)
	score=0.0
	try:
		score = word_freq * dict.get(word)
	except:
		None
	return score

def is_number(string):
	try:
		float(string)
		return True
	except:
		return False
def preprocess(text):
	'''
	@param text: original text (String)
	@param return: array of stemmed Words [] (Word is object with two attributes string,stem)
	'''
	match_apostrophes = re.compile(r'`|’')
	match_paragraphs = re.compile(r'[\.\?!\t\n\r\f\v]+')
	match_phrases = re.compile(r'[,;:\(\)\[\]\{\}<>]+')
	match_words = re.compile(r'[\w\-\'_/&]+')

	paragraphs = match_paragraphs.split(text)
	word_list = []
	for par in paragraphs:
		phrases = match_phrases.split(par)
		if len(phrases) > 0:
			for phr in phrases:
				words = match_words.findall(phr)
				if len(words) > 0:
					for w in words:
						if len(w) > 1 and not is_number(w): 
							word_list.append(Word(w,stem(w)))
	return word_list


def calculate_freq(word,text):
	'''
	@param word: (String) stemmed word 
	@param text: [] WordObj ,list of WordObj
	@param return: (float) representing the Frequency of the word in the document
	'''

	count = 0
	for w in text:
		if w.stem == word:
			count+=1
	return count/len(text)

rakeCache = collections.defaultdict(list)
def isRakeLabeled(word,text,textId): # word is already stemmed
	#run rake and extract tags 
	if len(rakeCache[textId]) == 0:
		rake_tags = rake.extract(text,6) # 6 is the highest F-SCORE FOUND (29.272%)
		rakeCache[textId] = rake_tags
	else:
		rake_tags = rakeCache[textId]
	for rake_tag in rake_tags:
		tags = rake_tag.split(' ')
		tags = map(stem,tags)
		if word in tags:
			return 1
	return 0

def getMaxScore(text):
	maximal = 0
	for word in text:
		score = get_score(word.stem,text)
		if score > maximal:
			maximal = score
	return maximal

def extract_features(textId,text,abstract,title,maximal,word,word_index,prev_word,next_word,second_prev_word,second_next_word):
	'''
		Depends on features in text or its title to extract relevance to the tag of that text
		-------------------------------------------
		FEATURES IMPLEMETED ARE DENOTED BY *
		FEATURES NOT IMPLEMETED ARE DENOTED BY **
		-------------------------------------------

		feature 1*: IDF (Inverse Document Frequency) > 0.2 of the maximal
					calcualted by word Frequency * IDF of that word in the corpus
		feature 2*: Tag is noun 
		feature 3*: part of the title (proved to be not very informative)
		feature 4**: RAKE Labeling
		feature 5*: Previous Word (the , a)
		feature 6*: Next Word (could be stopword)
		feature 7*: Second Previous Word
		feature 8*: Second Next Word
		feature 9*: Second Previous Word + Previous Word
		feature 10*: Previous Word + Current Word
		feature 11*: Current Word + Next Word
		feature 12*: Next Word + Second Next Word
		feature 13*: wordPost/LenOfDoc
		@param textId: (int) text index in database
		@param text: (String) the text to be tagged (pure Text Without stemming or preprocessing)
		@param abstract: ([] WordObj) Array Of single Words (Word object) of the text 
		@param title: (String) title of the text 
		@param word: (WordObj) current word
		@param word_index: (int) index of word in text
		@param prev_word: (WordObj) previous word
		@param next_word: (WordObj) next word
		@param second_prev_word: (WordObj) second previous word
		@param second_next_word: (WordObj) second next word
 		returns : dict of features
	NOTE : PAIRS HERE ARE REPRESENTED AS ONE TWO WORDS STRING SEPERATED BY A SPACE
	'''
	# POS TAGGING
	tagset = None
	tokens = nltk.word_tokenize(word.string)
	pos_tag = nltk.tag._pos_tag(tokens, tagset, pos_tagger)

	title = [stem(w) for w in title.split(' ')]
	text_length = len(abstract)
	features = {}
	word_score = get_score(word.stem,abstract) # calculate idf of the word
	

	features['idf'] = "%.2f" % word_score>0.2*maximal # precision to 1
	features['part_of_title'] = (word.stem in title) 
	features['previous_word'] = (prev_word.stem)
	features['next_word'] = (next_word.stem)
	features['second_prev_word'] = (second_prev_word.stem)
	features['second_next_word'] = (second_next_word.stem)
	features['second_prev_with_prev'] = second_prev_word.stem+' '+prev_word.stem
	features['prev_word_with_current'] = prev_word.stem+' '+word.stem
	features['current_word_with_next'] = word.stem+' '+next_word.stem
	features['next_word_with_sec_next'] = next_word.stem+' '+second_next_word.stem
	features['rake_labeled'] = (isRakeLabeled(word.string,text,textId))
	features['word_position'] = "%.2f" % (word_index+1/text_length) 
	features['pos_tag'] = (pos_tag[0][1])

	return features

def getTags(abstractId,all_tags):
	tags = []
	for tag in all_tags:
		if(tag[0] == abstractId):
			tags.append(tag[1])
	return tags

def is_tag(word,tags):
	for tag in tags:
		list = tag.split(' ')
		list = map(stem,list)
		if word.stem in list:
			return 'Tag'
	return 'NotTag'

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
	cursor.execute(query2)
	conn.commit()
	all_tags = cursor.fetchall()
 	for result_index,result in enumerate(train_set): 
		print "Progress: "+ str("{0:.2f}".format(result_index/len(train_set) * 100)) + '%'
		abstractId = int(result[0])
		title = str(result[1])
		text = str(result[2])
		abstract = preprocess(text)
		tags = getTags(abstractId,all_tags)
		maximal = getMaxScore(abstract)
		for word_index,word in enumerate(abstract):
			prev_word = abstract[word_index-1] if word_index-1 >= 0 else Word('')
			next_word = abstract[word_index+1] if word_index+1 < len(abstract) else Word('')
			second_prev_word = abstract[word_index-2] if word_index-2 >= 0 else Word('')
			second_next_word = abstract[word_index+2] if word_index+2 < len(abstract) else Word('')
			feature_train_set.append(
				(extract_features(abstractId,text,abstract,title,maximal,word,word_index,prev_word,next_word,second_prev_word,second_next_word),
					is_tag(word,tags))) 
	classifier = nltk.NaiveBayesClassifier.train(feature_train_set)
	f = open('naivebayes_classifier.cls', 'wb')
	pickle.dump(classifier, f)
	f.close()
