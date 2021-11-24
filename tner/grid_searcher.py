import glob
import json
import os
import logging
import string
import random
from typing import List
from itertools import product

from .trainer import Trainer
from .data import get_dataset, CACHE_DIR
from .language_model import TransformersNER


def get_random_string(length: int = 6, exclude: List = None):
    tmp = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    if exclude:
        while tmp in exclude:
            tmp = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    return tmp


def evaluate(model,
             export_dir,
             batch_size,
             max_length,
             data,
             lower_case: bool = False,
             data_cache_prefix: str = None):
    """ Evaluate question-generation model """
    if lower_case:
        path_metric = '{}/metric.lower.json'.format(export_dir)
    else:
        path_metric = '{}/metric.json'.format(export_dir)

    if os.path.exists(path_metric):
        with open(path_metric, 'r') as f:
            metric = json.load(f)
        return metric
    os.makedirs(export_dir, exist_ok=True)

    if model is not None:
        lm = TransformersNER(model)
        lm.eval()
        dataset_split, label_to_id, language, unseen_entity_set = get_dataset(data, lower_case=lower_case)

        def get_model_prediction_file(split):
            path_prediction = '{}/pred.{}.txt'.format(export_dir, split)
            if not os.path.exists(path_prediction):
                label = dataset_split[split]['label']
                pred = lm.predict(
                    dataset_split[split]['data'],
                    max_length=max_length,
                    batch_size=batch_size
                )

        hypothesis_file_dev = get_model_prediction_file('dev')
        hypothesis_file_test = get_model_prediction_file('test')
    else:
        assert hypothesis_file_dev is not None or hypothesis_file_test is not None, 'model or file path is needed'

    def get_metric(split, hypothesis_file):
        assert prediction_level in ['sentence', 'context'], prediction_level
        _metric, metric_individual = compute_metrics(
            out_file=hypothesis_file,
            tgt_file=reference_files['{}/question-processed'.format(split)],
            src_file=reference_files['{}/{}-processed'.format(split, prediction_level)],
            prediction_aggregation=prediction_aggregation,
            normalize=True,
            bleu_only=bleu_only)
        return _metric, metric_individual

    metric_dev, metric_individual_dev = get_metric('dev', hypothesis_file_dev)
    metric_test, metric_individual_test = get_metric('test', hypothesis_file_test)
    metrics_dict = {'dev': metric_dev, 'test': metric_test}
    with open(path_metric, 'w') as f:
        json.dump(metrics_dict, f)
    return metrics_dict


class GridSearcher:
    """ Grid search (epoch, batch, lr, random_seed, label_smoothing) """

    def __init__(self,
                 checkpoint_dir: str,
                 dataset: (str, List),
                 model: str = 'xlm-roberta-large',
                 fp16: bool = False,
                 lower_case: bool = False,
                 gradient_accumulation_steps: int = 4,
                 epoch: int = 10,
                 epoch_partial: int = 5,
                 n_max_config: int = 5,
                 max_length: int = 128,
                 max_length_eval: int = 256,
                 batch: int = 128,
                 batch_eval: int = 32,
                 crf: (List, bool) = True,
                 lr: (List, float) = 1e-4,
                 random_seed: (List, int) = 0):

        # evaluation configs
        self.eval_config = {'max_length_eval': max_length_eval}

        # static configs
        self.static_config = {
            'dataset': dataset,
            'model': model,
            'fp16': fp16,
            'gradient_accumulation_steps': gradient_accumulation_steps,
            'batch': batch,
            'epoch': epoch,
            'max_length': max_length,
            'lower_case': lower_case
        }

        # dynamic config
        self.epoch = epoch
        self.epoch_partial = epoch_partial
        self.batch_eval = batch_eval
        self.checkpoint_dir = checkpoint_dir
        self.n_max_config = n_max_config

        def to_list(_val):
            if type(_val) != list:
                return [_val]
            return sorted(_val, reverse=True)

        self.dynamic_config = {
            'lr': to_list(lr),
            'crf': to_list(crf),
            'random_seed': to_list(random_seed)
        }

        self.all_dynamic_configs = list(product(
            self.dynamic_config['lr'], self.dynamic_config['crf'], self.dynamic_config['random_seed']
        ))
        self.data_cache_dir = '{}/data_encoded/{}.{}.{}.{}'.format(
            CACHE_DIR,
            '_'.format(sorted(self.config.dataset)),
            self.static_config['model'],
            self.static_config['max_length'],
            'lower.' if self.static_config['lower_case'] else '.'
        )

    def initialize_searcher(self):
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        if os.path.exists('{}/config_static.json'.format(self.checkpoint_dir)):
            with open('{}/config_static.json'.format(self.checkpoint_dir)) as f:
                tmp = json.load(f)
            tmp_v = [tmp[k] for k in sorted(tmp.keys())]
            static_tmp_v = [self.static_config[k] for k in sorted(tmp.keys())]
            assert tmp_v == static_tmp_v, '{}\n not matched \n{}'.format(str(tmp_v), str(static_tmp_v))

        if os.path.exists('{}/config_dynamic.json'.format(self.checkpoint_dir)):
            with open('{}/config_dynamic.json'.format(self.checkpoint_dir)) as f:
                tmp = json.load(f)

            tmp_v = [tmp[k] for k in sorted(tmp.keys())]
            dynamic_tmp_v = [self.dynamic_config[k] for k in sorted(tmp.keys())]

            assert tmp_v == dynamic_tmp_v

        if os.path.exists('{}/config_eval.json'.format(self.checkpoint_dir)):
            with open('{}/config_eval.json'.format(self.checkpoint_dir)) as f:
                tmp = json.load(f)
            tmp_v = [tmp[k] for k in sorted(tmp.keys())]
            eval_tmp_v = [self.eval_config[k] for k in sorted(tmp.keys())]
            assert tmp_v == eval_tmp_v, '{}\n not matched \n{}'.format(str(tmp_v), str(eval_tmp_v))

        with open('{}/config_static.json'.format(self.checkpoint_dir), 'w') as f:
            json.dump(self.static_config, f)
        with open('{}/config_dynamic.json'.format(self.checkpoint_dir), 'w') as f:
            json.dump(self.dynamic_config, f)
        with open('{}/config_eval.json'.format(self.checkpoint_dir), 'w') as f:
            json.dump(self.eval_config, f)

        # add file handler
        logger = logging.getLogger()
        file_handler = logging.FileHandler('{}/grid_search.log'.format(self.checkpoint_dir))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
        logger.addHandler(file_handler)

        logging.info('INITIALIZE GRID SEARCHER: {} configs to try'.format(len(self.all_dynamic_configs)))

    def run(self):

        self.initialize_searcher()

        ###########
        # 1st RUN #
        ###########

        checkpoints = []

        ckpt_exist = {}
        for trainer_config in glob.glob('{}/model_*/trainer_config.json'.format(self.checkpoint_dir)):
            with open(trainer_config, 'r') as f:
                ckpt_exist[os.path.dirname(trainer_config)] = json.load(f)

        for n, dynamic_config in enumerate(self.all_dynamic_configs):
            logging.info('## 1st RUN: Configuration {}/{} ##'.format(n, len(self.all_dynamic_configs)))
            config = self.static_config.copy()
            tmp_dynamic_config = {
                'lr': dynamic_config[0],
                'crf': dynamic_config[1],
                'random_seed': dynamic_config[2]
            }
            config.update(tmp_dynamic_config)
            ex_dynamic_config = [(k_, [v[k] for k in sorted(tmp_dynamic_config.keys())]) for k_, v in ckpt_exist.items()]
            tmp_dynamic_config = [tmp_dynamic_config[k] for k in sorted(tmp_dynamic_config.keys())]
            duplicated_ckpt = [k for k, v in ex_dynamic_config if v == tmp_dynamic_config]

            if len(duplicated_ckpt) == 1:
                logging.info('skip as the config exists at {} \n{}'.format(duplicated_ckpt, config))
                checkpoint_dir = duplicated_ckpt[0]
            elif len(duplicated_ckpt) == 0:
                ckpt_name_exist = [os.path.basename(k).replace('model_', '') for k in ckpt_exist.keys()]
                ckpt_name_made = [os.path.basename(c).replace('model_', '') for c in checkpoints]
                model_ckpt = get_random_string(exclude=ckpt_name_exist + ckpt_name_made)
                checkpoint_dir = '{}/model_{}'.format(self.checkpoint_dir, model_ckpt)
            else:
                raise ValueError('duplicated checkpoints are found: \n {}'.format(duplicated_ckpt))

            if not os.path.exists('{}/epoch_{}'.format(checkpoint_dir, self.epoch_partial)):
                trainer = Trainer(checkpoint_dir=checkpoint_dir,
                                  disable_log=True,
                                  data_cache_path='{}.pkl'.format(self.data_cache_dir),
                                  **config)
                trainer.train(epoch_partial=self.epoch_partial, epoch_save=1)

            checkpoints.append(checkpoint_dir)

        path_to_metric_1st = '{}/metric.1st.json'.format(self.checkpoint_dir)

        metrics = {}
        for n, checkpoint_dir in enumerate(checkpoints):
            logging.info('## 1st RUN (EVAL): Configuration {}/{} ##'.format(n, len(checkpoints)))
            checkpoint_dir_model = '{}/epoch_{}'.format(checkpoint_dir, self.epoch_partial)
            try:
                metric = evaluate(
                    model=checkpoint_dir_model,
                    export_dir='{}/eval'.format(checkpoint_dir_model),
                    batch_size=self.batch_eval,
                    n_beams=self.eval_config['n_beams_eval'],
                    max_length=self.eval_config['max_length_eval'],
                    max_length_output=self.eval_config['max_length_output_eval'],
                    data=self.static_config['dataset'],
                    bleu_only=True
                )
            except Exception:
                logging.exception('ERROR IN EVALUATION')
                continue
            metrics[checkpoint_dir_model] = metric[self.split][self.metric]

        metrics = sorted(metrics.items(), key=lambda x: x[1], reverse=True)
        with open(path_to_metric_1st, 'w') as f:
            json.dump(metrics, f)

        logging.info('1st RUN RESULTS ({}/{})'.format(self.split, self.metric))
        for n, (k, v) in enumerate(metrics):
            logging.info('\t * rank: {} | metric: {} | model: {} |'.format(n, round(v, 3), k))

        if self.epoch_partial == self.epoch:
            logging.info('No 2nd phase as epoch_partial == epoch')
            return

        ###########
        # 2nd RUN #
        ###########

        metrics = metrics[:min(len(metrics), self.n_max_config)]
        checkpoints = []
        for n, (checkpoint_dir_model, _metric) in enumerate(metrics):
            logging.info('## 2nd RUN: Configuration {}/{}: {}/{} = {}'.format(
                n, len(metrics), self.split, self.metric, _metric))
            model_ckpt = os.path.dirname(checkpoint_dir_model)
            if not os.path.exists('{}/epoch_{}'.format(model_ckpt, self.epoch)):
                trainer = Trainer(checkpoint_dir=model_ckpt,
                                  disable_log=True,
                                  data_cache_path='{}.pkl'.format(self.data_cache_dir))
                trainer.train()

            checkpoints.append(model_ckpt)

        metrics = {}
        for n, checkpoint_dir in enumerate(checkpoints):
            logging.info('## 2nd RUN (EVAL): Configuration {}/{} ##'.format(n, len(checkpoints)))
            for checkpoint_dir_model in sorted(glob.glob('{}/epoch_*'.format(checkpoint_dir))):
                try:
                    metric = evaluate(
                        model=checkpoint_dir_model,
                        export_dir='{}/eval'.format(checkpoint_dir_model),
                        batch_size=self.batch_eval,
                        n_beams=self.eval_config['n_beams_eval'],
                        max_length=self.eval_config['max_length_eval'],
                        max_length_output=self.eval_config['max_length_output_eval'],
                        data=self.static_config['dataset'],
                        language=self.static_config['language'],
                        prediction_aggregation=self.eval_config['prediction_aggregation'],
                        prediction_level=self.eval_config['prediction_level'],
                        bleu_only=True
                    )
                except Exception:
                    logging.exception('ERROR IN EVALUATION')
                    continue

                metrics[checkpoint_dir_model] = metric[self.split][self.metric]

        metrics = sorted(metrics.items(), key=lambda x: x[1], reverse=True)
        logging.info('2nd RUN RESULTS: \n{}'.format(str(metrics)))
        for n, (k, v) in enumerate(metrics):
            logging.info('\t * rank: {} | metric: {} | model: {} |'.format(n, round(v, 3), k))

        with open('{}/metric.2nd.json'.format(self.checkpoint_dir), 'w') as f:
            json.dump(metrics, f)

