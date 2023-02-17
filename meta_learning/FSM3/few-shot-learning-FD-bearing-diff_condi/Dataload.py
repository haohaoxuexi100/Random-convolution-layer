# This code is modified from https://github.com/facebookresearch/low-shot-shrink-hallucinate
import torch
import pandas as pd
import numpy as np
import os
import h5py
from abc import abstractmethod
from torch.utils.data import DataLoader, Dataset
identity = lambda x: x

class SimpleDataset(Dataset):
    def __init__(self, data_file):
        f = h5py.File(data_file,'r') 
        self.X_orig = np.array(f['X'][:])
        self.Y_orig = np.array(f['Y'][:][0])

    def __getitem__(self, i):
        data = self.X_orig[i]
        label = self.Y_orig[i]
        return data, label

    def __len__(self):
        return self.X_orig.shape[0]


class SubDataset(Dataset):
    def __init__(self, sub_meta, cl):
        self.sub_meta = sub_meta
        self.cl = cl

    def __getitem__(self, i):
        data = self.sub_meta[i]
        target = self.cl
        return data, target

    def __len__(self):
        return len(self.sub_meta)


class MetaDataset(Dataset):
    def __init__(self, data_file, batch_size):
        f = h5py.File(data_file,'r') 
        X_orig = np.array(f['X'][:])
        Y_orig = np.array(f['Y'][:][0])
        #if train == True:
           #X_orig=torch.from_numpy(X_orig).float()
            #X_orig= X_orig.unsqueeze(dim=1)
            #N, C, W =  X_orig.size()
            #p = np.random.rand()
            #K = [1, 3, 5, 7, 11, 15]
            #if p > 0.5:
               #k = K[np.random.randint(0, len(K))]
                #Conv = torch.nn.Conv1d(1, 1, kernel_size=k, stride=1, padding=k//2, bias=False)
                #torch.nn.init.xavier_normal_(Conv.weight)
                #X_orig = Conv(X_orig.reshape(-1, C, W)).reshape(N, C*W)
                #X_orig =X_orig.detach().numpy()
            #else:
                #X_orig =X_orig 
        #else:
            #X_orig =X_orig

        self.cl_list = np.unique(Y_orig).tolist()

        self.sub_meta = {}
        for cl in self.cl_list:
            self.sub_meta[cl] = X_orig[np.where(Y_orig==cl)[0], :]

        self.sub_dataloader = []
        sub_data_loader_params = dict(batch_size=batch_size,
                                      shuffle=True,
                                      num_workers=0,  # use main thread only or may receive multiple batches
                                      pin_memory=False)
        for cl in self.cl_list:
            sub_dataset = SubDataset(self.sub_meta[cl], cl)
            self.sub_dataloader.append(torch.utils.data.DataLoader(sub_dataset, **sub_data_loader_params))

    def __getitem__(self, i):
        return next(iter(self.sub_dataloader[i]))

    def __len__(self):
        return len(self.cl_list)


class EpisodicBatchSampler(object):
    def __init__(self, n_classes, n_way, n_episodes):
        self.n_classes = n_classes
        self.n_way = n_way
        self.n_episodes = n_episodes

    def __len__(self):
        return self.n_episodes

    def __iter__(self):
        for i in range(self.n_episodes):
            yield range(self.n_classes)

class SimpleDataLoader:
    def __init__(self, batch_size, data_file):
        self.data_file = data_file
        self.batch_size = batch_size

        self.dataset = SimpleDataset(data_file)
        data_loader_params = dict(batch_size=self.batch_size, shuffle=True, num_workers=0, pin_memory=True)
        self.data_loader = DataLoader(self.dataset, **data_loader_params)


class MetaDataLoader:
    def __init__(self, data_file, n_way, n_support, n_query, n_eposide=100):
        self.data_file = data_file
        self.n_way = n_way
        self.batch_size = n_support + n_query
        self.n_eposide = n_eposide

        self.dataset = MetaDataset(data_file, self.batch_size)
        self.sampler = EpisodicBatchSampler(len(self.dataset), self.n_way, self.n_eposide)
        data_loader_params = dict(batch_sampler=self.sampler, num_workers=0, pin_memory=True)
        self.data_loader = DataLoader(self.dataset, **data_loader_params)
