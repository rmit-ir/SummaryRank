# SummaryRank

SummaryRank is a python package dedicated to supporting ranking experiments
over sentence/summary data.  It has implemented a range of basic functions,
such as data imports, representations/features generation, and feature vectors
split/join operations (for SVMLight format), to make ranking experiments easy.

This package supports the following sets of features:

* Query-biased summarization features from Metzler and Kanungo (2008) 
* ESA and Word2Vec features from Chen et al. (2015)
* TAGME feature and context meta-features from Yang et al. (2016)

If you use this package in your research work, please cite the following paper:

```
@inproceedings{yang_beyond_2016,
 author = {Yang, Liu and Ai, Qingyao and Spina, Damiano and Chen, Ruey-Cheng and
           Pang, Liang and Croft, W. Bruce and Guo, Jiafeng and Scholer, Falk},
 title = {Beyond Factoid {QA}: Effective Methods for Non-factoid Answer Sentence Retrieval},
 booktitle = {Proceedings of {ECIR} '16},
 year = {2016},
 pages = {115--128},
 publisher = {Springer}
}
```

## Get Started ##

To install all dependencies:

    pip install -r SummaryRank/requirements
    python -m nltk.downloader wordnet
    
To run the main script:

    SummaryRank/run.py <command>

SummaryRank will print out a list of supported tools if no command is specified.


## Notes for Replicating ECIR '16 Experiments ##

* An simple example script for extracting Metzler-Kanungo features
  is given in the directory `examples/`.

* We used two Galago indexes, one built over Gov2 as the background model 
  and the other over English Wikipedia for computing ESA.

  To build these indexes, you simply do (replace `galago` with the true Galago executable):

      galago --indexPath=/path/to/index --inputPath+/path/to/trectext --stemmer+krovetz --stemmer+porter
    
* Originally we used the English Wikipedia dump exported on May 15, 2015, but any 
  later version should also work.
  
* The `gen_freqstats` tool basically produces a `freqstats.gz` file, in which each line is of the form:

      <term> <term_frequency> <document_frequency>
  
  So one can essentially build this file from any custom resources.
  
  Note that the first line records collection level information.  We put total number of terms 
  in the field `term frequency` and total number of docs in `document_frequency`. Put any string
  as `term` as it is ignored in this case.

* The `gen_freqstats` tool can take an Indri index as input.


## Usage ##

### Import Data ###

SummaryRank put all processed data in a model directory (called *model*), so
upon the first execution, basic data will need to be imported.

Some import tools are available for these collections, which can be launched as commands:

* The [WebAP Dataset][] from CIIR/UMass (`import_webap`)
* [TREC Novelty Track Data][] (`import_trec_novelty`)
* [MobileClick-2][] (`import_mobileclick`)

One may need to specify a model directory using argument `-m` and supply a
list of raw files distributed with the benchmark.

To import WebAP data, for example, you can just do (replace WebAP files with true paths):

    SummaryRank/run.py import_webap -m webap WebAP/gradedText/gov2.query.json WebAP/gradedText/grade.trectext_patched


[WebAP Dataset]: https://ciir.cs.umass.edu/downloads/WebAP/
[TREC Novelty Track Data]: http://trec.nist.gov/data/novelty.html
[MobileClick-2]: http://www.mobileclick.org/

### Prepare Indexes ###

Certain tools such as `gen_freqstats` and `gen_esa` take [Galago][] indexes as input.

[Galago]: https://www.lemurproject.org/galago.php

### Generate Representations ###

Following the import, some of the intermediate data other than the raw texts
(called *representations*) may need to be generated.  These representations
serve as the input of downstream feature extractors.  This additional step
incorporates external resources or the output of external tools into the pipeline.

Currently, these representations are available:

* terms and stems (`gen_term`)
* term frequency stats (`gen_freqstats`)
* ESA representation (`gen_esa`)
* TAGME representation (`gen_tagme`)

To generate terms/stems (with both porter/krovetz stemmer supports):

    SummaryRank/run.py gen_term -m webap --stemmer krovetz

To generate term frequencies, which are required by retrieval function features
such as `LanguageModelScore` and `BM25Score`:

    SummaryRank/run.py gen_freqstats -m webap /path/to/index postings.krovetz

Note that the frequencies are pulled from a Galago inverted index, so one needs
to specify the index part (usually `postings.krovetz` or `posting.porter`).

To generate the ESA representation, with vector size (`-k`) and a Galago inverted
   index over the Wikipedia data as input:

    SummaryRank/run.py gen_esa -m webap /path/to/index

To generate the TAGME representation, with the API key to the TAGME web service as input:

    SummaryRank/run.py gen_tagme -m webap YOURAPIKEY
    
### Extract Features ###

SummaryRank currently has the following features built in:

* `SentenceLength`
* `SentenceLocation`
* `ExactMatch`
* `TermOverlap`
* `SynonymOverlap`
* `LanguageModelScore`
* `BM25Score`
* `ESACosineSimilarity`
* `Word2VecSimilarity`
* `TagmeOverlap`

All the feature extraction has to go through the `extract` tool.  The tool
takes a list of feature classnames as input, execute each of the nominated
extractors, and print out the produced feature vectors.  The output is in the
SVMLight format, and is usually stored in a gzip'ed format.

For example, the following command will extract the `SentenceLength` and
`TermOverlap` features from the WebAP data and store the compressed output to
some file.

    SummaryRank/run.py extract -m webap SentenceLength TermOverlap | gzip > two_features.txt.gz

Abbreviations to commonly used feature sets such as `MKFeatureSet` were also
available to save the user some typing.  For example, the following command
will extract all 6 Metzler-Kanungo features:

    SummaryRank/run.py extract -m webap MKFeatureSet | gzip > mk.txt.gz

Certain features may come with mandatory feature-related options.  This can be
revealed in the help screen at the very bottom ("dynamically generated") when
the classnames are given.  

    SummaryRank/run.py extract MKFeatureSet -h

### Generate Context Features ###

A special tool `contextualize` implements the extration of the context features
proposed in <a href="#yang_beyond_2016">Yang et al</a>.  It takes a feature
file (and optionally a list of selected fields via `-f`) as input.  For
example, this will contextualize the features 1, 4, 5, and 6 in the
vector file `mk.txt.gz`.

    SummaryRank/run.py contextualize -f 1,4-6 mk.txt.gz

### Manipulate the Feature Vector ###

SummaryRank also implements a set of data manipulation tools:

SummaryRank prepends a list of feature names as comments at the very beginning
of the feature-vector output (called *preamble*).  The `describe` tool can be
used to pull out this info.

    SummaryRank/run.py describe mk.txt.gz

The `cut` tool is used to extract certain fields (e.g., features) from the
vector file, resembling the function of the unix tool `cut`.  It takes the
vector file as input, and the field list is given via argument `-f`.  When the
argument `--renumbering` is specified, the feature IDs will be renumbered
starting from 1.  For example, the following will single out the features 2, 3,
5.

    SummaryRank/run.py cut mk.txt.gz -f2,3,5 | gzip > mk_primes.txt.gz

The `join` tool takes two or more vector files and merge them into one set.
Some of the feature will be renumbered.

    SummaryRank/run.py join mk_123.txt.gz mk_456.txt.gz | gzip > mk_full.txt.gz

The `shuffle` tool creates random shuffle over query topics, usually used
together with `split`.  A random seed can be specified through argument
`-seed`.

    SummaryRank/run.py shuffle mk.txt.gz | gzip > mk_shuffle.txt.gz

The `split` tool will split the data into multiple folds (via `-k`).  

    SummaryRank/run.py split -k 5 mk.txt.gz

The `normalize` tool is used to normalize features values.

    SummaryRank/run.py normalize mk.txt.gz | gzip > mk_normalized.txt.gz

## Contributors ##

* Ruey-Cheng Chen
* Damiano Spina
* Liu Yang
* Qingyao Ai

## References ##

<a name="chen_2015_harnessing"></a> Ruey-Cheng Chen, Damiano Spina, W. Bruce
Croft, Mark Sanderson, and Falk Scholer.  Harnessing semantics for answer
sentence retrieval.  In *Proceedings of the Eighth Workshop on Exploiting
Semantic Annotations in Information Retrieval*, ESAIR '15 (CIKM workshop),
pages 21&ndash;27. ACM, 2015.

<a name="metzler_2008_machine"></a> Donald Metzler and Tapas Kanungo.
Machine Learned Sentence Selection Strategies for Query-Biased Summarization.
In *Proceedings of SIGIR 2008 Learning to Rank Workshop*, pages 40&ndash;47.
ACM, 2008.

<a name="yang_2016_beyond"></a> Liu Yang, Qingyao Ai, Damiano Spina, Ruey-Cheng
Chen, Liang Pang, W. Bruce Croft, Jiafeng Guo and Falk Scholer.  Beyond factoid
QA: Effective methods for non-factoid answer sentence retrieval. In
*Proceedings of ECIR '16*, pages 115&ndash;128. Springer, 2016.

<a name="yulianti_2016_using"></a> Evi Yulianti, Ruey-Cheng Chen, Falk Scholer, 
and Mark Sanderson.  Using Semantic and Context Features for Answer Summary 
Extraction. In *Proceedings of ADCS '16*, pages 81-84. ACM, 2016.
