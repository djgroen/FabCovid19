
# FabCovid
This is a FabSim3 plugin for Covid-19 simulation


## Dependencies:

[FabSim3](https://github.com/djgroen/FabSim3.git) : `git clone https://github.com/djgroen/FabSim3.git`

[Flee - covid19 branch](https://github.com/djgroen/flee/tree/covid19) : `git clone -b covid19 https://github.com/djgroen/flee.git` 


## Installation
Simply type `fab localhost install_plugin:FabCovid19` anywhere inside your FabSim3 install directory.

### FabSim3 Configuration
Once you have installed the required dependencies, you will need to take a few small configuration steps:
1. Go to `(FabSim Home)/deploy`
2. Open `machines_user.yml`
3. Under the section `default:`, please add the following lines:
   <br/> a. `  flee_covid19_location=(Flee-covid19 PATH)`
   <br/> _NOTE: Please replace `Flee-covid19 PATH` with your actual install directory._
  
## Testing
1. To run a single job, simply type:
	>``` sh
	> fab <localhost/remote machine> covid19:<location_scenario>,<TS=transition scenario>,<TM=transition mode>,[outdir=output directory]
	> ```   
	> _NOTE:_
	> 	- **location_scenario** : _Currently 4 location scenario are available_ : `brent`, `ealing`, `harrow`, _and_ `hillingdon`.
	> 	- **TS** : _Acceptable Transition Scenario :._ `no-measures`,`extend-lockdown`,`open-all`,`open-schools`,`open-shopping`,`open-leisure`,`work50`,`work75`, and `work100`.
	> 	- **TM** : _Acceptable Transition Mode :._ `1`,`2`,and `3`.	
	> 	

2. To run the ensemble, you can type, simply type:
	>``` sh
	> fab localhost covid19_ensemble:location=<area_name>[,TS=transition scenario list][,TM=transition mode list]
	> ```   
	> _NOTE:_
	> 	-  By default, all _Acceptable_ Transition Scenario and Mode will be executed if these **TS** and **TM**  parameters did not passed
	>
	> _Examples:_
	> 	-  `fab localhost covid19_ensemble:location=harrow`
	> 	-  `fab localhost covid19_ensemble:location='brent;harrow;hillingdon'`
	> 	-  `fab localhost covid19_ensemble:location='harrow;hillingdon',TS='open-schools;open-shopping;open-leisure',TM='2;3'`	
	> 	

