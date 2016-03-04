SummaryRank
===========

SummaryRank is a python package dedicated to supporting ranking experiments
over sentence/summary data.  It has implemented a range of basic functions,
such as data imports, representations/features generation, and feature vectors
split/join operations (for SVMLight format), to make ranking experiments easy.

As of January 2016, this package supports the following sets of features:

* Query-biased summarization features from Metzler and Kanungo (2008) 
* ESA and Word2Vec features from Chen et al. (2015)
* TAGME feature and context meta-features from Yang et al. (2016)

If you use this package in your research work, please cite the following paper:

    Liu Yang, Qingyao Ai, Damiano Spina, Ruey-Cheng Chen, Liang Pang, W. Bruce Croft, 
    Jiafeng Guo and Falk Scholer.  Beyond factoid QA: Effective methods for non-factoid 
    answer sentence retrieval. In Proceedings of ECIR '16, to appear. 2016.


## Dependencies ##

The preferred way of running SummaryRank at this moment is simply through the `run.py`
script.  The package does not need to be explicitly installed, but quite a few
dependencies would need to be resolved through `pip`.  Usually, this is how you
get SummaryRank running on your machine:

    git clone https://github.com/rmit-ir/SummaryRank
    pip -r SummaryRank/requirements
    SummaryRank/run.py


## Usage ##

SummaryRank is designed to help researchers confront two essential but perhaps
tedious tasks in the ranking experiment: feature extraction and data
manipulation.  It helps break down the task of data munging into a number of
small but manageable steps.  

Some assumptions were made about the experimental task and the data:

* Your data has a set of *query topics*, each of these are associated with a
  set of *documents*.  Each of these documents contains one or more
  sub-document text units called *sentences*.

* Each query topic has a set of relevance judgments over sentences.  The
  purpose of your experiment is to rank the sentences with respect to the query
  topic.

### Import the Data ###

In the world of SummaryRank, a project-based repository (called *model*) is
always there hosting the processed data.  Therefore, on the first run, basic
data such as query topics, sentences, or relevance judgments will need to be
imported to create the new model.

We have implemented some import tools for the following test collections:

* The [WebAP Dataset][] from CIIR/UMass (`import_webap`)
* [TREC Novelty Track Data] (`import_trec_novelty`)
* [MobileClick-2] (`import_mobileclick`)

The respective corpora tool can be launched by running the command following
`SummaryRank/run.py`.  To use the import tools, one needs to specify a model
directory using argument `-m` and supply a list of raw files distributed with
the benchmark.  Detailed instructions for each of these tools are available in
the help screen (via argument `--help`).  

As an example, suppose you have downloaded the WebAP data and extracted all the
fileis under `WebAP`.  To import the data into a model directory named `webap`, you
just do:

    SummaryRank/run.py import_webap -m webap WebAP/gradedText/gov2.query.json WebAP/gradedText/grade.trectext_patched


[WebAP Dataset]: https://ciir.cs.umass.edu/downloads/WebAP/
[TREC Novelty Track Data]: http://trec.nist.gov/data/novelty.html
[MobileClick-2]: http://www.mobileclick.org/

### Generating Representations ###

Following the import, some of the intermediate data other than the raw texts
(called *representations*) may need to be generated.  These representations
serve as the input of downstream feature extractors.  For instance, some
features are based on word stems rather than words, some depends on term
frequency statistics from the inverted index, and some might need to invoke an
entity annotator.  This additional step allows us to incorporate external
resources or the output of external tools into the pipeline, by having a
separate set of representation *generators* to do the work.

Currently, for generating representations we have built in these tools:

* terms and stems (`gen_term`)
* term frequency stats (`gen_freqstats`)
* ESA representation (`gen_esa`)
* TAGME representation (`gen_tagme`)

Again in the help screen some descriptions about the tool is given.  Here's
some basic usage following our WebAP example:

1. Generate terms and stems.  (Both `porter` and `krovetz` stemmers are supported.)

    SummaryRank/run.py gen_term -m webap --stemmer krovetz

2. Generate term frequencies, required by retrieval function features
   such as `LanguageModelScore` and `BM25Score`.  The frequencies are pulled
   from a Galago inverted index; one also needs to specify the index part
   (usually `postings.krovetz` or `posting.porter`).

    SummaryRank/run.py gen_freqstats -m webap /path/to/index postings.krovetz

3. Generate the ESA representation, which is required by the `ESACosineSimilarity`
   feature.  One needs to specify the vector size (`-k`) and a Galago inverted
   index over the Wikipedia data.  Additional requirements on how this index
   should be prepared will be discussed later.

    SummaryRank/run.py gen_esa -m webap /path/to/index

4. Generate the TAGME representation, which is required by the `TagmeOverlap`
   feature.  One needs to specify the API key to the TAGME web service.

    SummaryRank/run.py gen_tagme -m webap YOURAPIKEY
    

### Extracting Features ###




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
