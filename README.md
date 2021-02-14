[![license](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://github.com/asahi417/tner/blob/master/LICENSE)
[![PyPI version](https://badge.fury.io/py/tner.svg)](https://badge.fury.io/py/tner)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/tner.svg)](https://pypi.python.org/pypi/tner/)
[![PyPI status](https://img.shields.io/pypi/status/tner.svg)](https://pypi.python.org/pypi/tner/)

# T-NER  
<p align="center">
  <img src="./asset/api.gif" width="600">
</p>

***`TNER`*** is a python tool to analyse language model finetuning on named-entity-recognition (NER), available via [pip](https://pypi.org/project/tner/). 
It has an easy interface to finetune models, test on cross-domain datasets with 9 publicly available NER datasets as well as custom datasets.
All models finetuned with `tner` can be deploy on our web app for visualization.
Finally, we release 46 XLM-RoBERTa model finetuned on NER on [transformers model hub](https://github.com/asahi417/tner/blob/master/MOEDL_CARD.md).

### Table of Contents  
1. **[Setup](#get-started)**
2. **[Model Finetuning](#model-finetuning)** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1AlcTbEsp8W11yflT7SyT0L4C4HG6MXYr?usp=sharing)
3. **[Model Evaluation](#model-evaluation)** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1jHVGnFN4AU8uS-ozWJIXXe2fV8HUj8NZ?usp=sharing)
4. **[Model Inference](#model-inference)** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]
4. **[Web API](#web-app):** Model deployment on a web-app   
5. **[Datasets](#datasets):** Built-in datasets and custom dataset

## Get Started
Install pip package
```shell script
pip install tner
```
or directly from the repository for the latest version.
```shell script
pip install git+https://github.com/asahi417/tner
```

## Model Finetuning
Language model finetuning on NER can be done with a few lines:
```python
import tner
trainer = tner.TrainTransformersNER(checkpoint_dir='path-to-checkpoint', dataset="data-name", transformers_model="transformers-model")
trainer.train()
```
where `transformers_model` is a pre-trained model name from [transformers model hub](https://huggingface.co/models) and
`dataset` is a dataset alias or path to custom dataset explained [dataset section](#datasets).
[Model files](https://huggingface.co/transformers/model_sharing.html#check-the-directory-before-pushing-to-the-model-hub) will be generated at `checkpoint_dir`, and it can be uploaded to transformers model hub without any changes.

To show validation accuracy at the end of each epoch,
```python
trainer.train(monitor_validation=True)
```
and to tune training parameter such as batch size, epoch, learning rate, please take a look [the argument description](https://github.com/asahi417/tner/blob/master/tner/model.py#L47).

***Train on multiple datasets:*** Model can be trained on a concatenation of multiple datasets by proviing a list of data name.
```python
trainer = tner.TrainTransformersNER(checkpoint_dir='./ckpt_merged', dataset=["ontonotes5", "conll2003"], transformers_model="xlm-roberta-base")
```
[Custom dataset](#custom-dataset) can be also added to it eg) `dataset=["ontonotes5", "./examples/custom_datas_ample"]`.

***Command line tool:*** Model finetune with CL tool.
```shell script
tner-train [-h] [-c CHECKPOINT_DIR] [-d DATA] [-t TRANSFORMER] [-b BATCH_SIZE] [--max-grad-norm MAX_GRAD_NORM] [--max-seq-length MAX_SEQ_LENGTH] [--random-seed RANDOM_SEED] [--lr LR] [--total-step TOTAL_STEP] [--warmup-step WARMUP_STEP] [--weight-decay WEIGHT_DECAY] [--fp16] [--monitor-validation] [--lower-case]
```

## Model Evaluation
Evaluation of NER models are easily done in/out of domain setting.
```python
import tner
trainer = tner.TrainTransformersNER(checkpoint_dir='path-to-checkpoint', transformers_model="language-model-name")
trainer.test(test_dataset='data-name')
```

***Entity span prediction:***  For better understanding of out-of-domain accuracy, we provide the entity span prediction
pipeline, which ignores the entity type and compute metrics only on the IOB entity position.
```python
trainer.test(test_dataset='data-name', entity_span_prediction=True)
```

***Command line tool:*** Model evaluation with CL tool.
```shell script
tner-test [-h] -c CHECKPOINT_DIR [--lower-case] [--test-data TEST_DATA] [--test-lower-case] [--test-entity-span]
```

## Model Inference
If you just want a prediction from a finetuned NER model, here is the best option for you.
```python
import tner
classifier = tner.TransformersNER('transformers-model')
test_sentences = [
    'I live in United States, but Microsoft asks me to move to Japan.',
    'I have an Apple computer.',
    'I like to eat an apple.'
]
classifier.predict(test_sentences)
```
***Command line tool:*** Model inference with CL tool.
```shell script
tner-predict [-h] [-c CHECKPOINT]
```

## Web App
To start the web app, first clone the repository
```shell script
git clone https://github.com/asahi417/tner
cd tner
```
then launch the server by
```shell script
uvicorn app:app --reload --log-level debug --host 0.0.0.0 --port 8000
```
and open your browser http://0.0.0.0:8000 once it's ready.
You can specify model to deploy by an environment variable `NER_MODEL`, which is set as `asahi417/tner-xlm-roberta-large-ontonotes5` as a defalt. 
`NER_MODEL` can be either path to your local model checkpoint directory or model name on transformers model hub.

***Acknowledgement*** The App interface is heavily inspired by [Multiple-Choice-Question-Generation-T5-and-Text2Text](https://github.com/renatoviolin/Multiple-Choice-Question-Generation-T5-and-Text2Text).

## Datasets
Public datasets that can be fetched with TNER is summarized here.

|                                   Name (`alias`)                                                                      |         Genre        |    Language   | Entity types | Data size (train/valid/test) | Note |
|:---------------------------------------------------------------------------------------------------------------------:|:--------------------:|:-------------:|:------------:|:--------------------:|:-----------:|
| OntoNotes 5 ([`ontonotes5`](https://www.aclweb.org/anthology/N06-2015.pdf))                                           | News, Blog, Dialogue | English       |           18 |   59,924/8,582/8,262 |  | 
| CoNLL 2003 ([`conll2003`](https://www.aclweb.org/anthology/W03-0419.pdf))                                             | News                 | English       |            4 |   14,041/3,250/3,453 |  |
| WNUT 2017 ([`wnut2017`](https://noisy-text.github.io/2017/pdf/WNUT18.pdf))                                            | SNS                  | English       |            6 |    1,000/1,008/1,287 |  |
| FIN ([`fin`](https://www.aclweb.org/anthology/U15-1010.pdf))                                                          | Finance              | English       |            4 |          1,164/-/303 |  |
| BioNLP 2004 ([`bionlp2004`](https://www.aclweb.org/anthology/W04-1213.pdf))                                           | Chemical             | English       |            5 |       18,546/-/3,856 |  |
| BioCreative V CDR ([`bc5cdr`](https://biocreative.bioinformatics.udel.edu/media/store/files/2015/BC5CDRoverview.pdf)) | Medical              | English       |            2 |    5,228/5,330/5,865 | split into sentences to reduce sequence length |
| WikiAnn ([`panx_dataset/en`, `panx_dataset/ja`, etc](https://www.aclweb.org/anthology/P17-1178.pdf))                  | Wikipedia            | 282 languages |            3 | 20,000/10,000/10,000 |  |
| Japanese Wikipedia ([`wiki_ja`](https://github.com/Hironsan/IOB2Corpus))                                              | Wikipedia            | Japanese      |            8 |              -/-/500 | test set only |
| Japanese WikiNews ([`wiki_news_ja`](https://github.com/Hironsan/IOB2Corpus))                                          | Wikipedia            | Japanese      |           10 |            -/-/1,000 | test set only |
| MIT Restaurant ([`mit_restaurant`](https://groups.csail.mit.edu/sls/downloads/))                                      | Restaurant review    | English       |            8 |        7,660/-/1,521 | lower-cased |
| MIT Movie ([`mit_movie_trivia`](https://groups.csail.mit.edu/sls/downloads/))                                         | Movie review         | English       |           12 |        7,816/-/1,953 | lower-cased |


To take a closer look into each dataset, one may want to use `tner.get_dataset_ner` as in
```python
import tner
data, label_to_id, language, unseen_entity_set = tner.get_dataset_ner('data-name')
```
where `data` consists of following structured data.
```
{
    'train': {
        'data': [
            ['@paulwalk', 'It', "'s", 'the', 'view', 'from', 'where', 'I', "'m", 'living', 'for', 'two', 'weeks', '.', 'Empire', 'State', 'Building', '=', 'ESB', '.', 'Pretty', 'bad', 'storm', 'here', 'last', 'evening', '.'],
            ['From', 'Green', 'Newsfeed', ':', 'AHFA', 'extends', 'deadline', 'for', 'Sage', 'Award', 'to', 'Nov', '.', '5', 'http://tinyurl.com/24agj38'], ...
        ],
        'label': [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], ...
        ]
    },
    'valid': ...
}
```

***WikiAnn dataset***  
All the dataset should be fetched automatically but not `panx_dataset/*` dataset, as you need to manually download data from
[here](https://www.amazon.com/clouddrive/share/d3KGCRCIYwhKJF0H3eWA26hjg2ZCRhjpEQtDL70FSBN?_encoding=UTF8&%2AVersion%2A=1&%2Aentries%2A=0&mgh=1)
(note that it will download as `AmazonPhotos.zip`) to the cache folder, which is `~/.cache/tner` as a default but can be changed by `cache_dir` argument in [training instance](https://github.com/asahi417/tner/blob/master/tner/model.py#L46) or [inference instance](https://github.com/asahi417/tner/blob/master/tner/model_prediction.py#L19).

### Custom Dataset
To go beyond the public datasets, user can use their own dataset by formatting them into
the IOB format described in [CoNLL 2003 NER shared task paper](https://www.aclweb.org/anthology/W03-0419.pdf),
where all data files contain one word per line with empty lines representing sentence boundaries.
At the end of each line there is a tag which states whether the current word is inside a named entity or not.
The tag also encodes the type of named entity. Here is an example sentence:
```
EU B-ORG
rejects O
German B-MISC
call O
to O
boycott O
British B-MISC
lamb O
. O
```
Words tagged with O are outside of named entities and the I-XXX tag is used for words inside a
named entity of type XXX. Whenever two entities of type XXX are immediately next to each other, the
first word of the second entity will be tagged B-XXX in order to show that it starts another entity.
The custom dataset should has `train.txt` and `valid.txt` file in a same folder. 
Please take a look [sample custom data](https://github.com/asahi417/tner/tree/master/examples/custom_dataset_sample).

