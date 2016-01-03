SummaryRank
===========

SummaryRank is a python package dedicated to supporting ranking experiments over sentence/summary data.  It has implemented a range of basic functions, such as data imports, representations/features generation, and feature vectors split/join operations (for SVMLight format), to make ranking experiments easy.

As of January 2016, this package supports the following sets of features:

* Query-biased summarization features from Metzler and Kanungo (2008) 
* ESA and Word2Vec features from Chen et al. (2015)
* TAGME feature and context meta-features from Yang et al. (2016)

If you use this package in your research work, please cite the following paper:

    Liu Yang, Qingyao Ai, Damiano Spina, Ruey-Cheng Chen, Liang Pang, W. Bruce Croft, 
    Jiafeng Guo and Falk Scholer.  Beyond factoid QA: Effective methods for non-factoid 
    answer sentence retrieval. In Proceedings of ECIR '16, to appear. 2016.

Detailed installation instructions and usage will be made available shortly.

## Contributors ##

* Ruey-Cheng Chen
* Damiano Spina
* Liu Yang
* Qingyao Ai

## References ##

<a name="chen_2015_harnessing"></a> Ruey-Cheng Chen, Damiano Spina, W. Bruce
Croft, Mark Sanderson, and Falk Scholer.  Harnessing semantics for answer
sentence retrieva.  In *Proceedings of the Eighth Workshop on Exploiting
Semantic Annotations in Information Retrieval*, ESAIR '15 (CIKM workshop),
pages 21&ndash;27. ACM, 2015.

<a name="metzler_2008_machine"></a> Donald Metzler and Tapas Kanungo.
Machine Learned Sentence Selection Strategies for Query-Biased Summarization.
In *Proceedings of SIGIR 2008 Learning to Rank Workshop*, pages 40&ndash;47.
ACM, 2008.

<a name="liu_2016_beyond"></a> Liu Yang, Qingyao Ai, Damiano Spina,
Ruey-Cheng Chen, Liang Pang, W. Bruce Croft, Jiafeng Guo and Falk Scholer.
Beyond factoid QA: Effective methods for non-factoid answer sentence
retrieval. In *Proceedings of ECIR '16*, to appear. 2016.
