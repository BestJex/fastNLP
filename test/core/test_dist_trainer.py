import unittest

import numpy as np
import torch.cuda
from fastNLP import DataSet
from fastNLP import Instance
from fastNLP import CrossEntropyLoss
from fastNLP import SGD
from fastNLP.core.dist_trainer import DistTrainer, get_local_rank
from fastNLP.models.base_model import NaiveClassifier
import shutil
import os
import subprocess
from argparse import ArgumentParser

def prepare_fake_dataset():
    mean = np.array([-3, -3])
    cov = np.array([[1, 0], [0, 1]])
    class_A = np.random.multivariate_normal(mean, cov, size=(1000,))

    mean = np.array([3, 3])
    cov = np.array([[1, 0], [0, 1]])
    class_B = np.random.multivariate_normal(mean, cov, size=(1000,))

    data_set = DataSet([Instance(x=[float(item[0]), float(item[1])], y=0) for item in class_A] +
                       [Instance(x=[float(item[0]), float(item[1])], y=1) for item in class_B])
    return data_set

def prepare_fake_dataset2(*args, size=100):
    ys = np.random.randint(4, size=100, dtype=np.int64)
    data = {'y': ys}
    for arg in args:
        data[arg] = np.random.randn(size, 5)
    return DataSet(data=data)

def set_rng_seed(seed):
    np.random.seed(seed)

class TestDistTrainer(unittest.TestCase):
    save_path = './save_cp'

    def run1(self):
        # test distributed training
        print('local rank', get_local_rank())
        set_rng_seed(100)
        data_set = prepare_fake_dataset()
        data_set.set_input("x", flag=True)
        data_set.set_target("y", flag=True)

        model = NaiveClassifier(2, 2)

        trainer = DistTrainer(
            model=model, train_data=data_set, optimizer=SGD(lr=0.1),
            loss=CrossEntropyLoss(pred="predict", target="y"),
            batch_size_per_gpu=8, n_epochs=3, print_every=50, save_path=self.save_path,
        )
        trainer.train()
        """
        # 应该正确运行
        """
        if trainer.is_master and os.path.exists(self.save_path):
            shutil.rmtree(self.save_path)

    def run2(self):
        # test fp16 with distributed training
        print('local rank', get_local_rank())
        set_rng_seed(100)
        data_set = prepare_fake_dataset()
        data_set.set_input("x", flag=True)
        data_set.set_target("y", flag=True)

        model = NaiveClassifier(2, 2)

        trainer = DistTrainer(
            model=model, train_data=data_set, optimizer=SGD(lr=0.1),
            loss=CrossEntropyLoss(pred="predict", target="y"),
            batch_size_per_gpu=8, n_epochs=3, print_every=50, save_path=self.save_path,
            fp16='O1'
        )
        trainer.train()
        """
        # 应该正确运行
        """
        if trainer.is_master and os.path.exists(self.save_path):
            shutil.rmtree(self.save_path)

    def run_dist(self, run_id):
        if torch.cuda.is_available():
            ngpu = min(4, torch.cuda.device_count())
            path = __file__
            cmd = ['python', '-m', 'torch.distributed.launch',
                   '--nproc_per_node', str(ngpu), path, '--test', str(run_id)]
            print(' '.join(cmd))
            retcode = subprocess.call(cmd)
            if retcode:
                raise RuntimeError('subprocess got non-zero exit status %d' % retcode)

    def test1(self):
        self.run_dist(1)

    def test2(self):
        self.run_dist(2)

if __name__ == '__main__':
    runner = TestDistTrainer()
    parser = ArgumentParser()
    parser.add_argument('--test', type=int)
    args, _ = parser.parse_known_args()
    if args.test and hasattr(runner, 'run%s'%args.test):
        getattr(runner, 'run%s'%args.test)()