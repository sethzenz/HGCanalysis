# HGCanalysis scripts

## Installation 

To add to your cmssw area

git clone git@github.com:PFCal-dev/HGCanalysis UserCode/HGCanalysis

To update in the remote

git push git@github.com:PFCal-dev/HGCanalysis

## GEN-SIM-RECO production

Use the generateEventsFromCfi.sh to steer the generation.
It will call cmsDriver.py and customize the configuration file.
The options can be inspected by calling:

generateEventsFromCfi.sh -h

A full production can be ran locally or submitted to the batch using 
the submitLocalHGCalProduction.py wrapper script. Two examples are given below:

### Particle gun 

For muons it's enough a single energy

#default geometry
python scripts/submitLocalHGCalProduction.py -q 1nd -n 10 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/Single13_${CMSSW_VERSION} -p 13 -n 100 -e 100";
#change geometry scenario
python scripts/submitLocalHGCalProduction.py -q 1nd -n 100 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/Single13_v4_${CMSSW_VERSION} -p 13 -n 100 -e 100 -g Extended2023HGCalV4Muon,Extended2023HGCalV4MuonReco";

For regression use flat gun

python scripts/submitLocalHGCalProduction.py -q 1nd -n 250 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/FlatPtYSingle11_${CMSSW_VERSION} -c UserCode/HGCanalysis/python/particlePtYGun_cfi.py -n 500 -p 11";

For calibration use 100 events per file x 100 jobs

energies=(5 10 20 30 50 75 100 150 250 500)
pids=(11 22 211 130)
for pid in ${pids[@]}; do
    for en in ${energies[@]}; do
	#default geometry
    	python scripts/submitLocalHGCalProduction.py -q 1nd -n 100 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/Single${pid}_${CMSSW_VERSION} -p ${pid} -n 100 -e ${en}";
	#change geometry scenario
	#python scripts/submitLocalHGCalProduction.py -q 1nd -n 100 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/Single${pid}_v4_${CMSSW_VERSION} -p ${pid} -n 100 -e ${en} -g Extended2023HGCalV4Muon,Extended2023HGCalV4MuonReco";
     done
done

#test alternative physics lists for pions
phys=("QGSP_FTFP_BERT_EML" "FTFP_BERT_EML" "FTFP_BERT_XS_EML" "QBBC")
pids=(211)
energies=(30)
for pid in ${pids[@]}; do
    for en in ${energies[@]}; do
    	for p in ${phys[@]}; do
        python scripts/submitLocalHGCalProduction.py -q 1nd -n 10 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/Single${pid}_${CMSSW_VERSION}_${p} -p ${pid} -n 400 -e ${en} -l ${p}";
        done
    done
done

### Minimum bias (1000 events per file x 500 jobs, should be ok for later mixing with particle gun)

python scripts/submitLocalHGCalProduction.py -q 2nd -n 500 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/MinBias_${CMSSW_VERSION} -c UserCode/HGCanalysis/python/minBias_cfi.py -n 500";

python scripts/submitLocalHGCalProduction.py -q 2nd -n 500 -s generateEventsFromCfi.sh -o "-o /store/cmst3/group/hgcal/CMSSW/MinBias_v4_${CMSSW_VERSION} -c UserCode/HGCanalysis/python/minBias_cfi.py -n 500 -g Extended2023HGCalV4Muon,Extended2023HGCalV4MuonReco";

### Other processes

Can use the minimum bias example, just substitute the argument passed in the -c option to point to the new cfi snippet.

### Redigitization with pileup mixing (will run one job per file, randomizing the min.bias files at start)

taus=(0 10 20)
pids=(13)
for tau in ${taus[@]}; do
    for pid in ${pids[@]}; do
        inputFiles=(`cmsLs /store/cmst3/group/hgcal/CMSSW/Single${pid}_${CMSSW_VERSION}`);
	nFiles=${#inputFiles[@]};
	python scripts/submitLocalHGCalProduction.py -n ${nFiles} -q 1nd -s redigitizeAndMix.sh -o "-o /store/cmst3/group/hgcal/CMSSW/Single${pid}_${CMSSW_VERSION}_v2/tau_${tau} -t Single${pid}_${CMSSW_VERSION}_v2 -m MinBias_${CMSSW_VERSION} -p ${tau}";
done
done
    

## Producing analysis ntuples

The ntuples are produced by plugins/HGCSimHitsAnalyzer.cc.  Change the code according to your needs.
To submit the production of the ntuples you can use the following script (it will printout the options)

cmsRun runHGCSimHitsAnalyzer_cfg.py

Submit several jobs to the batch and store the output in EOS

pids=(11 211)
ifiles=(0 100 200 300 400 500 600 700)
for pid in ${pids[@]}; do
    for ifile in ${ifiles[@]}; do
    	cmsRun test/runHGCSimHitsAnalyzer_cfg.py Single${pid}_${CMSSW_VERSION}_v2 ${ifile} 100 & 
    done
done
