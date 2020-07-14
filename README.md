
# FabCovid19
FabCovid19 is a FabSim3 plugin for Flu And Coronavirus Simulator (FACS). 
### A step-by-step guide for Execution of FACS Simulation at sub-national level using local and HPC resources.

## Preface

In this tutorial, you will get step-by-step guidance on the usage of FabCovid19 components to simulate FACS simulations within a local and HPC execution environment. In this tutorial you will learn about the following FabCovid19 software components and how these components are used in COVID-19 prediction application as shown in the Tube Map below:

![Graphical depiction of the FabCovid19 components used in the FACS Simulation tutorial](https://raw.githubusercontent.com/djgroen/FabCovid19/master/FabCovid19Map.png)

-   [FabSim3](https://fabsim3.readthedocs.io/) - an automation toolkit that features an integrated test infrastructure and a flexible plugin system. 
-   [FACS](https://github.com/djgroen/facs/blob/master/README.md) - an agent based simulation framework that models the viral spread at the sub-national level, incorporating geospatial data sources to extract buildings and residential areas within a predefined region.
-   [QCG Pilot Job](https://wiki.vecma.eu/qcg-pilotjobs) - a Pilot Job system that allows to execute many subordinate jobs in a single scheduling system allocation,

## Contents
  * [Infectious Disease simulations](#infectious-disease-simulations)
  * [Dependencies](#Dependencies)
  * [Installation of required software packages](#installation)
  * [FabSim3 Configuration](#fabSim3-configuration)
  * [Execution](#execution)
  * [Acknowledgements](#acknowledgements)
  
## Infectious Disease simulations
FabCovid19 is a FACS toolkit plugin for infectious disease simulation which automates complex simulation workflows. In this tutorial, we demonstrate different types of FACS simulations. We explain how you can do create an agent-based disease transmission model of a specific infectious disease e.g., COVID-19 and forecast its spread over space and time. This tutorial demonstrates the model construction and steps to perform a set of runs based on different lockdown scenarios, and visualize the spread of infections across space and time with confidence intervals. 

### Dependencies:

1. [FabSim3](https://github.com/djgroen/FabSim3.git)
To install the Fabsim3 automation toolkit, see the [installation](https://fabsim3.readthedocs.io/en/latest/installation.html#installing-fabsim3) documentation. 
2. [FACS: Flu And Coronavirus Simulator](https://github.com/djgroen/facs) 
To install FACS in your working directory, simply type:
```
git clone https://github.com/djgroen/facs.git
``` 

### Installation
To install FabCovid19, simply go to the FabSim3 directory and type 
```
fab localhost install_plugin:FabCovid19
```

#### FabSim3 Configuration
Once you have installed the required dependencies, you will need to take a few small configuration steps:
1. Go to `(FabSim3 Home)/deploy`
2. Open `machines_user.yml`
3. Under the section `default:`, please add the following lines:
   <br/> `facs_location=(facs PATH)`
   <br/> NOTE: Please replace `facs PATH` with your actual install directory.
  
### Execution
1. To run a single job, simply type:
	>``` sh
	> fab <localhost/remote machine> covid19:<location_scenario>,<TS=transition scenario>,<TM=transition mode>,[outdir=output directory]
	> ```   
	> _NOTE:_
	> 	- **location_scenario** : _Currently 4 location scenario are available_ : `brent`, `ealing`, `harrow`, _and_ `hillingdon`.
	> 	- **TS** : _Acceptable Transition Scenario :._ `no-measures`,`extend-lockdown`,`open-all`,`open-schools`,`open-shopping`,`open-leisure`,`work50`,`work75`,  `work100`, and `dynamic-lockdown`.
	> 	- **TM** : _Acceptable Transition Mode :._ `1`,`2`,`3`,and `4`.	
	>
	> _Example:_
	>	-  `fabsim localhost covid19:harrow,TS=periodic-lockdown,TM=1,ci_multiplier=0.3,cores=1,job_wall_time=6:00:00` 	

2. To run the ensemble, you can type, simply type:
	>``` sh
	> fab <localhost/remote machine> covid19_ensemble:location=<area_name>[,TS=transition scenario list][,TM=transition mode list]
	> ```   
	> _NOTE:_
	> 	-  By default, all _Acceptable_ Transition Scenario and Mode will be executed if these **TS** and **TM**  parameters did not passed
	>
	> _Examples:_
	> 	-  `fabsim localhost covid19_ensemble:location=harrow`
	> 	-  `fabsim localhost covid19_ensemble:location='brent;harrow;hillingdon'`
	> 	-  `fabsim localhost covid19_ensemble:location='harrow;hillingdon',TS='open-schools;open-shopping;open-leisure',TM='2;3'`	
	> 	
3. If you ran an ensemble jobs, you may need to do averaging across runs on the output `csv` files before plotting, in that case you can type:
   >``` sh
	> fab <localhost/remote machine> cal_avg_csv:<location_scenario>,<TS=transition scenario>,<TM=transition mode>
	> ```   
	> _Examples:_
	> 	- submit an ensambe jobs
	>       `fabsim eagle_hidalgo covid19_ensemble:location='brent',TS='extend-lockdown;dynamic-lockdown',TM='1',cores=1,PilotJob=true,replicas=25`
	>    - fetching results 
	> 	 `fabsim eagle_hidalgo fetch_results'`
	>   -  Averaging across runs 
	> 	-  `fabsim eagle_hidalgo cal_avg_csv:brent,TS='extend-lockdown',TM=1,cores=1`
	> 	-  `fabsim eagle_hidalgo cal_avg_csv:brent,TS='dynamic-lockdown',TM=1,cores=1`		
	> 	

## Acknowledgements

This work was supported by the HiDALGO and VECMA projects, which has received funding from the European Union Horizon 2020 research and innovation programme under grant agreement No 824115 and 800925.
