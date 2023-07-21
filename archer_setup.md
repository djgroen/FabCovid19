# Running FACS on ARCHER2 Supercomputer using FabCovid19

## Pre-requisites

In order to get FACS running on ARCHER2, you need the following

1. An account on ARCHER2
2. An installation of FabSim3 on your local machine 
3. An installation of FabCovid19 plugin within FabSim3

This tutorial assumes that you have the above-mentioned pre-requisites. In other words:

1. You are able to login to ARCHER2 using the command

   ```bash
   ssh uname@login.archer2.ac.uk
   ```

   where `uname` is your ARCHER2 username.

2. You are able to run commands such as

   ```bash
   fabsim localhost covid19_ensemble:configs=brent,cores=4,simulation_period=100,measures='measures_uk',starting_infections=0.001
   ```

## Objective

After completing this tutorial, you should be able to successfully run commands such as

```bash
fabsim archer2 covid19_ensemble:configs=brent,cores=4,simulation_period=100,measures='measures_uk',starting_infections=0.001
```

In  other words, you should be able to run FACS on ARCHER2 by simply replacing `localhost` with `archer2`. And given the power of supercomputers, you should be able to run bigger ensembles such as

```bash
fabsim archer2 covid19_ensemble:configs=brent,cores=8,simulation_period=100,measures='measures_uk',starting_infections=0.001,replicas=50
```

without much hassle.

## The Setup

This setup assumes the following:

- Your ARCHER2 username is `uname`
- You are associated with the project code `p123`
- You want to use resources from the budget code `p123-test`
- The latest installation of FabSim3 on your local machine is at `/path/to/FabSim3`

In all the subsequent code that follows, please replace these by the variables associated with you.

Follow the steps listed below

### Modifications on the remote machine

1. From your local machine, login to ARCHER2 using

   ```bash
   ssh uname@login.archer2.ac.uk
   ```

2. Add the following lines to `~/.bashrc`

   ```bash
   export PYTHONUSERBASE=/work/p123/p123/uname/.local
   export PATH=$PYTHONUSERBASE/bin:$PATH
   export PYTHONPATH=$PYTHONUSERBASE/lib/python3.8/site-packages:$PYTHONPATH
   ```

   Save the changes, exit the editor and log out and back in into ARCHER2.


3. From your home directory in ARCHER2, issue the following commands

   ```bash
   module load cray-python
   pip3 install --user pyyaml
   ```

4. Now move to your work directory using

   ```bash
   cd /work/p123/p123/uname
   ```

5. Clone FACS in your work directory

   ```bash
   git clone git@github.com:djgroen/facs.git
   ```

6. Logout of ARCHER2 to your local machine using

   ```bash
   logout
   ```



### Modifications on the local machine

1. Add the following lines to the file `~/.ssh/config`

   ```bash
   Host archer2
      User uname
      HostName login.archer2.ac.uk
      ControlPath ~/.ssh/controlmasters/%r@%h:%p
      ControlMaster auto
      ControlPersist 30m
   ```

   Save the changes and exit the editor.

2. Create a directory using

   ```bash
   mkdir ~/.ssh/controlmasters
   ```

3. Modify your existing `/path/to/FabSim3/fabsim/deploy/machines_user.yml` file such that it contains the following:

   ```yaml
   archer2:
     username: "uname"
     manual_ssh: true
     facs_location: "/work/p123/p123/uname/facs"
     remote: "archer2"
     project: "p123"
     budget: "p123-test"
     job_wall_time: "1:00:00"
     run_prefix_commands: ["export PYTHONUSERBASE=/work/p123/p123/uname/.local", "export PATH=$PYTHONUSERBASE/bin:$PATH", "export PYTHONPATH=$PYTHONUSERBASE/lib/python3.8/site-packages:$PYTHONPATH"]
   ```

   

   
