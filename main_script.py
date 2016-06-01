import subprocess
import os
import shutil
import collections
import pickle
import nltk	
import sys
import operator
import run_classifier as cls
##################### COMMANDS ############################
# ffmpeg -i vinput.mp4 -acodec pcm_s16le -ac 1 -ar 16000 output1.wav 
# ffmpeg -ss %startAt -t %captureTime -i in.wav out.wav
# java -Xmx2024m -jar ./LIUM_SpkDiarization-8.4.1.jar  --fInputMask=./output2.wav --sOutputMask=./output2.seg --doCEClustering  output2
# pocketsphinx_continuous -infile  > output.txt
#################### BEAM COMMENTS ###########################
#  -beam			1e-48		Beam width applied to every frame in Viterbi search (smaller values mean wider beam)
#  -fwdflatbeam		1e-64		Beam width applied to every frame in second-pass flat search
#  -fwdflatwbeam		7e-29		Beam width applied to word exits in second-pass flat search
#  -lpbeam			1e-40		Beam width applied to last phone in words
#  -lponlybeam		7e-29		Beam width applied to last phone in single-phone words
#  -outlatbeam		1e-5		Minimum posterior probability for output lattice nodes
#  -pbeam			1e-48		Beam width applied to phone transitions
#  -pl_beam		1e-10		Beam width applied to phone loop search for lookahead
#  -pl_pbeam		1e-10		Beam width applied to phone loop transitions for lookahead
#  -wbeam			7e-29		Beam width applied to word exits
# pocketsphinx_batch -hmm model/en-us/ -dict dictionary/cmudict-en-us.dict -adcin yes -cepdir wavFiles -cepext .wav -ctl test.ctl -hyp test.hyp
###############################################################
reload(sys)  # put in because nltk expects UNICODE chars 
sys.setdefaultencoding('utf8')
videosDir = "videos"
wavFilesPATH = "/home/abdoo/Desktop/Bachelor/wavFiles/"
segmentsInfoPATH = "./wavFiles-segInfo/"
segmentsPATH = "./wavFiles-seg/"
controlFile = "./controlFile.ctl"
outputTextPATH = "./outputText/"
tagsDictionaryPATH = "./data/tagsDictionary/dict.pkl"
candidateTagsPATH = "./candidateTags/"
testsPATH = "./tests/"
taggerPATH = "./ext_lib/tagger/"
# Beam Stuff
beam = '1e-48'						# Default = 1e-48	
fwdflatbeam = '1e-64'			# Default = 1e-64
fwdflatwbeam = '7e-29'		# Default = 7e-29	
lpbeam = '1e-40'					# Default = 1e-40
lponlybeam = '7e-29'			# Default = 7e-29
outlatbeam = '1e-5'				# Default = 1e-5
pbeam = '1e-48'						# Default = 1e-48	
pl_beam = '1e-10'					# Default = 1e-10
pl_pbeam = '1e-10'				# Default = 1e-10
wbeam = '7e-29'						# Default = 7e-29
### End Of Beam Stuff
segPathArr = []
wavFilesNames = []

############### CLEAR ALL TEMP DIRECTORIES ####################
for root,subDirs,files in os.walk(segmentsPATH):
	for f in files:
		os.unlink(os.path.join(root, f))
	for d in subDirs:
		shutil.rmtree(os.path.join(root, d))

for root,subDirs,files in os.walk(wavFilesPATH):
	for f in files:		
		os.unlink(os.path.join(root, f))
for root,subDirs,files in os.walk(segmentsInfoPATH):
	for f in files:		
		os.unlink(os.path.join(root, f))
print 'Temporary Folders & Files Cleared !!!'
############## Helper Methods ##################
def segmentAudio(file,wavFile,segID):
	for line in file:
		if line.startswith(";"): # a commented line in LIUM segmentation File starts with ';'
			continue
		fields = line.strip().split() # fields[2]: segment starts At, fields[3]: Length of Segment
		startAt = str(float(fields[2])/100)
		length = str(float(fields[3])/100)
		wavFilesNames.append(wavFile[:-4]+'_seg_'+str(segID))
		segmentProcess = subprocess.Popen(['ffmpeg','-ss',startAt,'-t',length,'-i',wavFilesPATH+wavFile,wavFile[:-4]+'/'+wavFile[:-4]+'_seg_'+str(segID)+'.wav'],cwd=segmentsPATH)		
		segID+=1
		segmentProcess.communicate()[0]
##################### END OF HELPERS ######################

################ SCRIPT BEGIN #########################


####################### Extract Audio Layer ##########################
for root,subDirs,files in os.walk(videosDir):
	for file in files:
		extWavProcess = subprocess.Popen(['ffmpeg','-i','%s' %(file),'-acodec','pcm_s16le','-ac','1','-ar','16000','%s' %(wavFilesPATH+file[:-4]+'.wav')],cwd=videosDir)
		extWavProcess.communicate()[0] # exit the current subprocess
		wavFilesNames.append(file)
print "DONE With Wav Extraction!!!"
print "Constructing Control File"
with open(controlFile, 'w') as myfile:
	for filename in wavFilesNames:
		print >> myfile, filename
##################### Extract Segmentation Info ############################
print "Extracting Segmentation Info ..."
for root,subDirs,files in os.walk(wavFilesPATH):
	for file in files:
		subprocess.call(['java','-Xmx2024m','-jar','./LIUM_SpkDiarization-8.4.1.jar','--fInputMask','%s' %(wavFilesPATH+file),'--sOutputMask','%s' %(segmentsInfoPATH+file+'.seg'),'--doCEClustering',file])
##################### Segmenting ###########################
for root,subDirs,files in os.walk(segmentsInfoPATH):
 	for file in files:
 		full_path = os.path.join(segmentsInfoPATH, file)
 		wavFileName = str(file)[:-4]
 		print 'Segmenting ' + file + '...............'
 		segID = 0 # initialy 0
 		os.makedirs(segmentsPATH+wavFileName[:-4])
 		segPathArr.append(wavFileName[:-4])
 		segmentAudio(open(full_path),wavFileName,segID)
print 'Segments Created !!!'
with open(controlFile, 'w') as myfile:
	for filename in wavFilesNames[1:]:
		print >> myfile, filename
####################### Extracting Text (PocketSphinx Call) ##############################
# 		for file in files:
# 			extWordProcess = subprocess.Popen('pocketsphinx_continuous -infile %s >> %s' %(segmentsPATH+sub+'/'+file,outputTextPATH+sub+'.txt'),shell=True)
# 			extWordProcess.communicate()[0]
print 'Extracting Text ....'
for root,subDirs,files in os.walk(segmentsPATH):
	for subDir in subDirs:
		path = root+subDir
		extWordProcess = subprocess.Popen('pocketsphinx_batch -hmm %s -dict %s -lm %s -adcin yes -cepdir %s -cepext .wav '
																			'-ctl %s -hyp %s -beam	%s -fwdflatbeam %s -fwdflatwbeam %s -lpbeam %s ' 
																			'-lponlybeam %s -outlatbeam %s -pbeam %s -pl_beam	%s -pl_pbeam %s -wbeam %s' 
																		%('data/acousticModel/en-us/',
																			'data/dictionary/en-us/cmudict-en-us.dict',
																			'data/languageModel/en-us/en-us.lm',
																			path,
																			controlFile,
																			'outputText.hyp',
																			beam,
																			fwdflatbeam,
																			fwdflatwbeam,
																			lpbeam,
																			lponlybeam,
																			outlatbeam,
																			pbeam,
																			pl_beam,
																			pl_pbeam,
																			wbeam),
																		shell=True)
extWordProcess.communicate()[0]
for root,subDirs,files in os.walk(outputTextPATH):
	for file in files:
		with open(outputTextPATH+file, 'r') as myfile:
			data=myfile.read().replace('\n', '')
################ Applying Tagging Algorithm #########################
print "Applying NaiveBayes Classifier ..."
print "Extracting Tags..."
print 'DONE !!!'
print "Extracted Tags Are: "
cls.main()

