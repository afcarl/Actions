import torch
import torch.optim as optim
import torch.nn as nn
from torch.autograd import Variable
from tqdm import trange
import math


def repackage_hidden(h):
    """Wraps hidden states in new Variables, to detach them from their history."""
    if type(h) == Variable:
        return Variable(h.data)
    else:
        return tuple(repackage_hidden(v) for v in h)


class test():
    def __init__(self, model, model_rn18, avg_pool, data_loader, data_len, n_inp, args):

        super(test, self).__init__()
        self.model = model
        self.data_loader = data_loader
        self.data_len = data_len
        self.model_rn18 = model_rn18
        self.avg_pool = avg_pool
        self.args = args
        self.n_inp = n_inp

        # Error logger
        self.logger_bw = open(args.save + '/test_error_bw.log', 'w')
        self.logger_bw.write('{:10}'.format('Test Error'))
        self.logger_bw.write('\n{:-<10}'.format(''))


    def forward(self):
        args = self.args
        data_loader = self.data_loader
        model = self.model

        loss_fn = nn.CrossEntropyLoss()
        model.eval()
        total_error = 0
        input_3Dsequence = torch.FloatTensor(1, 3, 6, args.dim[1], args.dim[0])
        y = torch.FloatTensor(1, self.n_classes)
        if args.cuda:
            input_3Dsequence = input_3Dsequence.cuda()
            y = y.cuda()

        pbar = trange(len(data_loader.dataset), desc='Testing  ')

        for batch_idx, (data_batch_seq, target_batch_seq) in enumerate(data_loader):
            # Data is of the dimension: batch_size x frames x 3 x height x width
            n_frames = data_batch_seq.size(1)
            state = model.init_hidden(args.bs)

            if args.cuda:  # Convert into CUDA tensors
                target_batch_seq = target_batch_seq.cuda()
                data_batch_seq = data_batch_seq.cuda()

            seq_pointer = 0
            for seq_idx in range(n_frames):
                input_3Dsequence[0, :, seq_pointer, :, :] = data_batch_seq[:, seq_idx]
                seq_pointer += 1

                state = repackage_hidden(state)

                if seq_pointer == 6:
                    y, state = model(Variable(input_3Dsequence), state)
                    temp_loss = loss_fn(y[-1], Variable(target_batch_seq))
                    seq_pointer = 0

                    # Log batchwise error
                    self.logger_bw.write('\n{:.6f}'.format(temp_loss.data[0]))

            loss = loss_fn(y[-1], Variable(target_batch_seq))

            # `clip_grad_norm` helps prevent the exploding gradient problem in RNNs / LSTMs.
            # torch.nn.utils.clip_grad_norm(model.parameters(), args.clip)

            if batch_idx % 10 == 0:
                if (batch_idx*len(data_batch_seq) + 10) <= len(data_loader.dataset):
                    pbar.update(10)
                else:
                    pbar.update(len(data_loader.dataset) - batch_idx*len(data_batch_seq))

            total_error += loss.data[0]         # Total loss
        total_error = total_error/math.ceil(self.data_len/args.bs)
        pbar.close()
        return total_error