# AutomaticVideoTagging
This is part of a bachelor project aimed at the extraction of keywords refering to the context of the topic of a video

to be able to run it, first download the latest english acoustic model, dictionary ,language model from sphinx official site and put it in folder data in the root dir of the project.
also for testing purposes, you can download datasets from the following link: https://github.com/snkim/AutomaticKeyphraseExtraction
Folder dataset include 3 scripts responsible for writing the datasets to a database, configure these to your need.

current accuracy reached on text 43% in F-Score. the accuracy of the whole system depends on the accuracy of sphinx system.

Main_script is used to run the project
MachineLearning_naiveBayes is used for training a classifier.
