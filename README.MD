# UMA calculator interface for Gaussian, ORCA6 and GRRM, and simple optimization script

## Abstract
This is a interface program to use Meta's UMA (universal neural network potential) based on Omol25 [ https://arxiv.org/abs/2505.08762 ] for Gaussian16, ORCA6, GRRM programs.
You need to obtain a parameter file from Huggin Face [ https://huggingface.co/facebook/UMA ]. `umaopt` is a simple structure optimization script.
 
## Software version
We tested this interface with Gaussian16 RevC01, GRRM23, ORCA 6.1.0/6.0.1
We used Python 3.12, torch==2.6.0, fairchem-core==2.3.0.

## Create Python Environment for UMA with fairchem-core
uv [https://docs.astral.sh/uv/] is recommended to create virtual environment. After installing uv, please create venv as follows.
if you want to use GPU, install appropriate GPU version of torch.
Test on GPU calculations were performed with cuda 12.6.3 docker environment with the same torch/fairchem-core versions as the CPU version. 
```
mkdir ~/venv
cd ~/venv
uv venv --python 3.12 uma
source uma/bin/activate
uv pip install torch==2.6.0
uv pip install fairchem-core==2.3.0
```
Before running calculation, you need to activate this venv by
```
source ~/venv/uma/bin/activate
```

In addition, you need to appropriately setup ORCA or GRRM you want to use.

## Setup this Interface and parameter file
Just copy all script files in one directory and add the directory to PATH.
Download parameter files and place it into the same directory.
```
/opt/uma
├── _common_utils.py
├── gau2umas
├── grrm2umas
├── orca2umas
├── uma-m-1p1.pt
├── umaopt
├── umas
├── uma-s-1p1.pt
└── uma-s-1.pt
```

```
export PATH=/opt/uma:$PATH
```

## How does it work?
Because loading the model file and preparing the calculator show a large overhead compared to actual calculation, the calculator server (umas) is created before running ORCA/GRRM in background and then calculation is performed via socket communication. Calculations should be run as follows.

```
umas start &
COMMAND TO RUN CALCULATION
umas exit
```

When starting umas, port number is automatically set and saved in `/tmp/umas_port_${JOB_ID}.json`.
`${JOB_ID}` is automatically set from the environmental variable: `${UMA_JOBID}` `${PBS_JOBID}` `${LSB_JOBID}` `${SLURM_JOB_ID}` `${PJM_JOBID}`. If not set, `{$USER}_default` is used. This ID must be unique to avoid confusion of socket communication. When you run a job in a queuing system such as PBS or Slurm, you might not need to care because the corresponding JOB ID is set by the queuing system. In other cases, please set `${UMA_JOBID}` with a unique string. 

## Calculate with GPU
Add `--gpu` or `-g` option.
```
umas start --gpu &
COMMAND TO RUN CALCULATION
umas exit
```

Currently, fairchem seems to be unable to use GPU number like 'cuda:0' but just to use 'cuda' as device. 
When GPU is selected, num_threads set by ORCA interface (same as ORCA pal) or by user (GRRM) is not meaningful
because it is only for CPU threading.

By adding `-p N` option, you can start multiple calculation workers (see GRRM Multiprocess Job).
In this case, one GPU is used by one worker, and the other workers use cpu.
For example, in the following case, 1 workers use GPU and the other 3 workers use CPU.
```
umas start -p 4 --gpu &
COMMAND TO RUN CALCULATION
umas exit
```

## Select model
Add `--model NAME` options as below.
```
umas start --model s0  # Old model uma-s-1.pt (s0 or small0)
umas start --model s   # model uma-s-1p1.pt (s or small) [default]
umas start --model m   # model uma-m-1p1.pt (m or medium)
```

## Gaussian16
Input file (route section) is be as follows. For opt, opt=nomicro is necessary.
```
# SP External='gau2umas'
# OPT=(nomicro,maxcycle=1000) External='gau2umas'
```
Batch shell script is as follows. It is noted that the thread parallelization should be given as environmental variable `UMA_THREADS` or `OMP_NUM_THREADS`. `%nprocshared` does not affect the thread parallelization of uma calculation.
```
# Setup g16 before here
source ~/venv/uma/bin/activate
export PATH=/opt/uma:$PATH

# number of cpu core to be used. OMP_NUM_THREADS can also work.
export UMA_THREADS=8

umas start &
g16 jobname.gjf
umas exit
```

## ORCA6
Input file is be as follows. Only energy and gradient calculations are available. If you need freq, please select NumFreq.
```
! ExtOPT TightOpt

%method
 ProgExt "/opt/uma/orca2umas"
end

*xyz 0 1
... (cartesian)
*
```
Batch shell script is as follows.
```
# Setup ORCA before here
source ~/venv/uma/bin/activate
export PATH=/opt/uma:$PATH
ORCA_EXEC=`which orca`

umas start &
${ORCA_EXEC} jobname.inp > jobname.out
umas exit
```

## GRRM Single Process Job
Input file (com) is as follows. MinFC=-1 or NOFC is recommended if possible. Hessian calculation by UMA (ASE Calculator) is performed numerically,
meaning that 6N gradient calculations are necessary and it takes a long time.

```
%link=non-supported
#MIN

0 1
... (cartesian)
Options
sublink=grrm2umas
MinFC=-1

```

When using GRRM, charge, spin multiplicity, and thread parallelization of single job must be given as following environmental variables. **The spin and multiplicity in the com file are just IGNORED**. 

```
export UMA_CHARGE=1
export UMA_MULTI=1
export UMA_THREADS=4
```

Batch shell script is as follows.

```
# Setup ORCA before here
source ~/venv/uma/bin/activate
export PATH=/opt/uma:$PATH

export UMA_CHARGE=1
export UMA_MULTI=1
export UMA_THREADS=4

# Run
umas start & 
GRRM23p jobname -s36000
umas exit
```

## GRRM Multiprocess Job (AFIR search)
Input file (com) is as follows. 
```
%link=non-supported
# MC-AFIR
 
0 1
... (cartesian)
Options
NoFC
sublink=grrm2umas
NFault = 100
Add Interaction
Fragm.1 = ...
Fragm.2 = ...
1 2
GAMMA = 300
END
```

The following `${UMA_THREAD}` value is for each process. 

```
export UMA_CHARGE=1
export UMA_MULTI=1
export UMA_THREADS=2
```

Batch shell script is as follows. When starting umas, `--np` or `-p` options should be added to create multiple calulation workers. In the following case, 10 processes x 2 threads = 20 cores are used. 

```
# Setup ORCA before here
source ~/venv/uma/bin/activate
export PATH=/opt/uma:$PATH

export UMA_CHARGE=1
export UMA_MULTI=1
export UMA_THREADS=2

# Run
umas start -p 10 & 
GRRM23p jobname -s36000 -p10
umas exit
```

## Simple Optimizer (ASE LBFGS optimizer)

`umaopt` is a simple optimizer to use xyz file as an input. In case multiple structures are included, all the structures are optimized with the same settings. The comment lines of the outpuf files are energies in Hartree unit, which would be useful when using crest/cregen for sorting and clustering.

**Usage**
```
# Simple optimization, input_umaopt.xyz (converged) or input_umaopt_faied.xyz (failed).
$ umaopt input.xyz

# Optimization runs with 4 parallel processes and each process uses 2 cpu threads
$ umaopt input.xyz -p 4 -t 2

# Optimization using GPU (1 process)
$ umaopt input.xyz --gpu
```

**Optimization with Atom Constraints**

Optimizations can be performed with fixing several atoms, which is useful for preoptimization of transition state structures.
`--constrain` option is followed by atom indices (1-based, NOT 0-based like in ASE).
The following examples run optimization with atom 8,10,64,65,66,67 fixed.

```
umaopt init.xyz --constrain 8,10,64,65,66,67
```

**Other Commandline Options**
```
--charge <int>, -c <int>: Total charge
--mult <int>, -m <int>: Spin multiplicity
--fmax <float>: Convergence criteria (same as ASE)
--maxcycle <int>: Max cycles of optimization
```
