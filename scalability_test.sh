#!/bin/bash

cd ../../

FABSIM_DIR=($PWD)
echo $FABSIM_DIR

cores=( 6 5 4 3 2 1 12 24)

FABRIC_DIR="/home/plgrid/plgarabnejad/FACS_easyvvuq/FabSim3"
END=3

for C in "${cores[@]}"
do
	sum=0
	for i in $(seq 1 $END)
	do
		/bin/rm -rf $FABSIM_DIR/deploy/.jobscripts/*

		ssh plgarabnejad@eagle.man.poznan.pl "rm -rf $FABRIC_DIR/results/* ; rm -rf $FABRIC_DIR/config_files/* ; rm -rf $FABRIC_DIR/scripts/*"

		fab eagle_vecma covid19_init_SC:location=brent,nb_thread=$C,PilotJob=True,virtualenv=true,TestOnly=True

		sleep 5.0
	done
done



