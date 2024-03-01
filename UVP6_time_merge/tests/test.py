import sys
sys.path.append('/remote/complex/home/fpetit/UVP6_time_merge')
from time_merge.functions import read_acq

data = ["Data_test/Data/20210612-120000/20210612-120000_data.txt"]

test = read_acq(data)

print(test)