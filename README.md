# UMA calculator interface for ORCA6 and GRRM

## Abstract
This is a interface program to use Meta's UMA (universal neural network potential) based on Omol25 [ https://arxiv.org/abs/2505.08762 ] for ORCA6 and GRRM programs.
All the calculations are performed using CPU, NOT GPU.
You need to obtain a parameter file from Huggin Face [ https://huggingface.co/facebook/UMA ]. 

## Software version
We tested this interface with GRRM23, ORCA 6.0.1.
We used Python 3.12, torch==2.6.0, fairchem-core==2.2.0.

## Create Python Environment for UMA with fairchem-core
uv [https://docs.astral.sh/uv/] is recommended to create virtual environment. After installing uv, please create venv as follows.
```
mkdir ~/venv
cd ~/venv
uv venv --python 3.12 uma
source uma/bin/activate
uv pip install torch==2.6.0
uv pip install fairchem-core==2.2.0
```
Before running calculation, you need to activate this venv by
```
source ~/venv/uma/bin/activate
```

In addition, you need to appropriately setup ORCA or GRRM you want to use.

## Setup this Interface and parameter file
Just copy all script files in one directory and add the directory to PATH.
Download parameter file (uma-s-1.pt) and place it into the same directory.
```
/opt/uma
├── _common_utils.py
├── grrm2umas
├── orca2umas
├── umas
└── uma-s-1.pt
```

```
export PATH=/opt/uma:$PATH
```

## How does it work?
As loading the model file and prepare the calculator shows a large overhead compared to actual calculation, the calculator server (umas) is created before running ORCA/GRRM in background and then calculation is performed via socket communication. Calculations should be run as follows.

```
umas start &
COMMAND TO RUN CALCULATION
umas exit
```

When starting umas, port number is automatically set and saved in `/tmp/umas_port_${JOB_ID}.json`.
`${JOB_ID}` is automatically set from the environmental variable: `${UMA_JOBID}` `${PBS_JOBID}` `${LSB_JOBID}` `${SLURM_JOB_ID}` `${PJM_JOBID}`. If not set, `{$USER}_default` is used. This ID must be unique to avoid confusion of socket communication. When you run a job in a queuing system such as PBS or Slurm, you might not need to care because the corresponding JOB ID is set by the queuing system. In other cases, please set `${UMA_JOBID}` with a unique string. 


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

