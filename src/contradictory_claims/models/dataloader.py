"""DataLoader and Dataclasses classes required for required for SBERT"""

from collections import Counter

import torch
from torch.utils.data import Dataset
from sentence_transformers.readers import InputExample


class ClassifierDataset(Dataset):

    def __init__(self, dataframe, tokenizer):
        """Initializer for Classifier Dataset

        :param dataframe: The dataframe containing the NLI data
        :type dataframe: Pandas DataFrame
        :param tokenizer: The tokenizer used in the model
        :type tokenizer: Huggingface tokenizers
        """
        self.sentence1 = dataframe.sentence1.values
        self.sentence2 = dataframe.sentence2.values
        self.label = dataframe.label.values
        self.tokenizer = tokenizer

    def __getitem__(self, index):
        return (self.tokenized(self.sentence1[index])), (self.tokenized(self.sentence2[index])), self.label[index]

    def tokenized(self, text):
        """Return the tokens generated from processing the sentence.

        :param text: text for which token to be calculated
        :type text: string
        :return: tokens generated from the text
        :rtype: list
        """
        return self.tokenizer.encode_plus(text,
                                          max_length=512,
                                          pad_to_max_length=True,
                                          truncation=True)["input_ids"]

    def class_weight(self):
        """Returns the class weights to tackle skewness in data while training.

        :return: torch tensor of weights
        :rtype: torch.tensor
        """
        target_list = self.label
        count_dict = Counter(target_list)
        class_count = [count_dict[i] for i in range(3)]
        class_weights = len(target_list) / torch.tensor(class_count, dtype=torch.float)
        class_weights = class_weights / class_weights.sum()
        print(class_weights)
        return class_weights

    @staticmethod
    def get_labels():
        return {"contradiction": 0, "neutral": 2, "entailment": 1}

    def __len__(self):
        return len(self.label)


class NLIDataReader(object):
    def __init__(self, dataframe):
        self.df = dataframe.copy()

    def get_examples(self, max_examples: int = None):
        if max_examples is None:
            max_examples = self.df.shape[0]
        s1 = self.df["sentence1"].iloc[:max_examples].values
        s2 = self.df["sentence2"].iloc[:max_examples].values
        labels = self.df["label"].astype(int).iloc[:max_examples].values
        examples = []
        for guid_id, (sentence_a, sentence_b, label) in enumerate(zip(s1, s2, labels)):
            examples.append(InputExample(guid=guid_id, texts=[sentence_a, sentence_b], label=label))
        return examples

    @staticmethod
    def get_labels():
        return {"contradiction": 0, "entailment": 2, "neutral": 1}

    def get_num_labels(self):
        return len(self.get_labels())

    def map_label(self, label):
        return self.get_labels()[label.strip().lower()]


def multi_acc(y_pred: torch.tensor, y_test: torch.tensor):
    """Calculate the accuracy of the output from the SBERT model.

    :param y_pred: tensor containing output from the SBERT model
    :type y_pred: torch.tensor
    :param y_test: tensor containing actual labels
    :type y_test: torch.tensor
    :return: accuracy of the model
    :rtype: torch.tensor
    """
    y_pred_softmax = torch.log_softmax(y_pred, dim=1)
    _, y_pred_tags = torch.max(y_pred_softmax, dim=1)
    correct_pred = (y_pred_tags == y_test).float()
    acc = correct_pred.sum() / len(correct_pred)
    acc = torch.round(acc * 100)
    return acc


def collate_fn(batch):
    """Collate function used for Dataloader

    :param batch: Dataloader sends a batch of items
    :return: modified batch
    """
    sentence1 = [item[0] for item in batch]
    sentence2 = [item[1] for item in batch]
    label = [item[2] for item in batch]
    label = torch.tensor(label)
    return sentence1, sentence2, label