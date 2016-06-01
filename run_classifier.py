import re
import pickle
import machine_learning_naivebayes as mln
import run_classifier_database as rcd

def filterCandidateKeywords(keywords):
	'''
	@param keywords: candidate keywords for filtering 
	@param number: (int)number of tags
	@return [] String: filtered list where that list is sorted by the score of each tag
	'''
	print "Filtering Candidate Keywords..."
	phrase_list = rcd.getAllPhrases(text)
	sorted_keywords = rcd.sortAccordingToScore(keywords,phrase_list)
	return sorted_keywords

def main():
	classifier = pickle.load(open('naivebayes_classifier.cls'))
	textFile = "./outputText.hyp"
	text = ""
	title = ""
	candidateKeywordsList = []
	with open(textFile, 'r') as myfile:
		for line in myfile:
			text+=re.sub(r'\(.*?\)', '', line) # remove parentheses

		preprocessedText = mln.preprocess(text)
		maximal = mln.getMaxScore(preprocessedText)
		for index,word in enumerate(preprocessedText):
			prev_word = preprocessedText[index-1] if index-1 >= 0 else mln.Word('')
			next_word = preprocessedText[index+1] if index+1 < len(preprocessedText) else mln.Word('')
			second_prev_word = preprocessedText[index-2] if index-2 >= 0 else mln.Word('')
			second_next_word = preprocessedText[index+2] if index+2 < len(preprocessedText) else mln.Word('')
			ruling = classifier.classify(
				mln.extract_features(
					0,text,preprocessedText,title,maximal,word,index,prev_word,next_word,second_prev_word,second_next_word))
			if(ruling == "Tag"):
				candidateKeywordsList.append(word.string)

		print candidateKeywordsList[:6]
