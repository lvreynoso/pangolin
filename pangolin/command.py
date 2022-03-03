#!/usr/bin/env python3
from . import _program
from pangolin import __version__

# try:
#     import pangoLEARN
# except:
#     install_error("pangoLEARN", "https://github.com/cov-lineages/pangoLEARN.git")

# try:
#     from pangoLEARN import PANGO_VERSION
# except:
#     sys.stderr.write(cyan('Error: please update to pangoLEARN version >= 2021-05-27\n'))
#     sys.exit(-1)

try:
    import pangolin_data
except:
    install_error("pangolin_data", "https://github.com/cov-lineages/pangolin_data.git")

try:
    import scorpio
except:
    install_error("scorpio", "https://github.com/cov-lineages/scorpio.git")

try:
    import constellations
except:
    install_error("constellations", "https://github.com/cov-lineages/constellations.git")

import os
import sys
import argparse

try:
    import snakemake
except:
    sys.stderr.write(cyan(f'Error: package `{snakemake}` not found, please install snakemake or update pangolin environment.\n'))
    sys.exit(-1)


from pangolin.utils.log_colours import green,cyan
from pangolin.utils import dependency_checks

from pangolin.utils import data_checks
from pangolin.utils import update


from pangolin.utils.config import *
from pangolin.utils.initialising import *
import pangolin.utils.io_parsing as io

from pangolin.utils.report_collation import generate_final_report,get_voc_list

thisdir = os.path.abspath(os.path.dirname(__file__))
cwd = os.getcwd()

def main(sysargs = sys.argv[1:]):
    parser = argparse.ArgumentParser(prog = _program,
    description='pangolin: Phylogenetic Assignment of Named Global Outbreak LINeages',
    usage='''pangolin <query> [options]''')

    io_group = parser.add_argument_group('Input-Output options')
    io_group.add_argument('query', nargs="*", help='Query fasta file of sequences to analyse.')
    io_group.add_argument('-o','--outdir', action="store",help="Output directory. Default: current working directory")
    io_group.add_argument('--outfile', action="store",help="Optional output file name. Default: lineage_report.csv")
    io_group.add_argument('--tempdir',action="store",help="Specify where you want the temp stuff to go. Default: $TMPDIR")
    io_group.add_argument("--no-temp",action="store_true",help="Output all intermediate files, for dev purposes.")
    io_group.add_argument('--alignment', action="store_true",help="Output multiple sequence alignment.")
    io_group.add_argument('--alignment-file', action="store",help="Multiple sequence alignment file name.")

    a_group = parser.add_argument_group('Analysis options')
    a_group.add_argument('--analysis-mode', action="store",help="Specify which inference engine to use. Options: accurate (UShER), fast (pangoLEARN), pangolearn, usher. Default: UShER inference.")
    
    # a_group.add_argument('--use-assignment-cache', action="store_true",help="Use cache file from pango-assignment to speed up lineage assignment.", dest="assignment_cache")
    a_group.add_argument("--skip-designation-cache", action='store_true', default=False, help="Developer option - do not use designation cache to assign lineages.",dest="skip_designation_cache")

    a_group.add_argument('--max-ambig', action="store", default=0.3, type=float,help="Maximum proportion of Ns allowed for pangolin to attempt assignment. Default: 0.3",dest="maxambig")
    a_group.add_argument('--min-length', action="store", default=25000, type=int,help="Minimum query length allowed for pangolin to attempt assignment. Default: 25000",dest="minlen")

    d_group = parser.add_argument_group('Data options')
    d_group.add_argument("--update", action='store_true', default=False, help="Automatically updates to latest release of pangolin, pangolin-data, scorpio and constellations, then exits.")
    d_group.add_argument("--update-data", action='store_true',dest="update_data", default=False, help="Automatically updates to latest release of constellations and pangolin-data, including the pangoLEARN model, UShER tree file and alias file, then exits.")
    d_group.add_argument('-d', '--datadir', action='store',dest="datadir",help="Data directory minimally containing the pangoLEARN model, header files and UShER tree. Default: Installed pangolin-data package.")
    d_group.add_argument('--usher-tree', action='store', dest='usher_protobuf', help="UShER Mutation Annotated Tree protobuf file to use instead of --usher default from pangolin-data repository or --datadir.")

    m_group = parser.add_argument_group('Misc options')
    m_group.add_argument("--aliases", action='store_true', default=False, help="Print Pango alias_key.json and exit.")
    m_group.add_argument("-v","--version", action='version', version=f"pangolin {__version__}")
    m_group.add_argument("-pv","--pangolin-data-version", action='version', version=f"pangolin-data {pangolin_data.__version__}",help="show version number of pangolin data files (UShER tree and pangoLEARN model files) and exit.")
    m_group.add_argument("--all-versions", action='store_true',dest="all_versions", default=False, help="Print all tool, dependency, and data versions then exit.")
    m_group.add_argument("--verbose",action="store_true",help="Print lots of stuff to screen")
    m_group.add_argument("-t","--threads",action="store",default=1,type=int, help="Number of threads")


    if len(sysargs)<1:
        parser.print_help()
        sys.exit(-1)
    else:
        args = parser.parse_args(sysargs)

    # Initialise config dict
    config = setup_config_dict(cwd)
    data_checks.check_install(config)
    set_up_verbosity(config)

    if args.update:
        update.update({'pangolin': __version__,
                'pangolin-data': config[KEY_PANGOLIN_DATA_VERSION],
                'constellations': config[KEY_CONSTELLATIONS_VERSION],
                'scorpio': config[KEY_SCORPIO_VERSION]
                })

    if args.update_data:
        update.update({'pangolin-data': config[KEY_PANGOLIN_DATA_VERSION],
                'constellations': config[KEY_CONSTELLATIONS_VERSION]}, 
                args.datadir)

    # Parsing analysis mode flags to return one of 'usher', 'pangolearn' or 'assignment_cache'
    config[KEY_ANALYSIS_MODE] = set_up_analysis_mode(args.analysis_mode, config[KEY_ANALYSIS_MODE])
    print(green(f"****\nPangolin running in {config[KEY_ANALYSIS_MODE]} mode.\n****"))
    snakefile = get_snakefile(thisdir,config[KEY_ANALYSIS_MODE])

    setup_data(args.datadir,config[KEY_ANALYSIS_MODE], config)
    config[KEY_DESIGNATION_CACHE],config[KEY_ALIAS_FILE] = data_checks.find_designation_cache_and_alias(config[KEY_DATADIR],DESIGNATION_CACHE_FILE,ALIAS_FILE)
    if args.aliases:
        print_alias_file_exit(config[KEY_ALIAS_FILE])

    if args.all_versions:
        print_versions_exit(config)

    # to enable not having to pass a query if running update
    # by allowing query to accept 0 to many arguments
    
#   setup outdir and outfiles
    config[KEY_OUTDIR] = io.set_up_outdir(args.outdir,cwd,config[KEY_OUTDIR])
    config[KEY_OUTFILE] = io.set_up_outfile(args.outfile, config[KEY_OUTFILE],config[KEY_OUTDIR])
    io.set_up_tempdir(args.tempdir,args.no_temp,cwd,config[KEY_OUTDIR], config)
    config[KEY_ALIGNMENT_FILE],config[KEY_ALIGNMENT_OUT] = io.parse_alignment_options(args.alignment, config[KEY_OUTDIR], config[KEY_TEMPDIR],args.alignment_file, config[KEY_ALIGNMENT_FILE])

    config[KEY_QUERY_FASTA] = io.find_query_file(cwd, config[KEY_TEMPDIR], args.query)

    io.quick_check_query_file(cwd, args.query, config[KEY_QUERY_FASTA])

    if config[KEY_ANALYSIS_MODE] == "usher":
        # needed data is usher protobuf file
        config[KEY_USHER_PB] = data_checks.get_usher_protobuf_arg(args.usher_protobuf,cwd)
        data_checks.get_datafiles(config[KEY_DATADIR],usher_files,config)

    elif config[KEY_ANALYSIS_MODE] == "pangolearn":
        # find designation cache and the model files
        data_checks.get_datafiles(config[KEY_DATADIR],pangolearn_files,config)

    # elif config[KEY_ANALYSIS_MODE] == "assignment_cache":
    #     # look for the assignment cache, and also the ??? files (usher or pangolearn?)
    #     config[KEY_ASSIGNMENT_CACHE] = data_checks.get_cache()

    preprocessing_snakefile = get_snakefile(thisdir,"preprocessing")

    if args.verbose:
        print(green("\n**** CONFIG ****"))
        for k in sorted(config):
            print(green(k), config[k])

        status = snakemake.snakemake(preprocessing_snakefile, printshellcmds=True, forceall=True, force_incomplete=True,
                                        workdir=config[KEY_TEMPDIR],config=config, cores=args.threads,lock=False
                                        )
    else:
        logger = custom_logger.Logger()
        status = snakemake.snakemake(preprocessing_snakefile, printshellcmds=False, forceall=True,force_incomplete=True,workdir=config[KEY_TEMPDIR],
                                    config=config, cores=args.threads,lock=False,quiet=True,log_handler=logger.log_handler
                                    )
    if status: # translate "success" into shell exit code of 0
       
        if config[KEY_VERBOSE]:
            print(green("\n**** CONFIG ****"))
            for k in sorted(config):
                print(green(k), config[k])

            status = snakemake.snakemake(snakefile, printshellcmds=True, forceall=True, force_incomplete=True,
                                            workdir=config[KEY_TEMPDIR],config=config, cores=args.threads,lock=False
                                            )
        else:
            logger = custom_logger.Logger()
            status = snakemake.snakemake(snakefile, printshellcmds=False, forceall=True,force_incomplete=True,workdir=config[KEY_TEMPDIR],
                                        config=config, cores=args.threads,lock=False,quiet=True,log_handler=logger.log_handler
                                        )
        
       
        if status: 
            
            ## Collate the report here

            preprocessing_csv = os.path.join(config[KEY_TEMPDIR],"preprocessing.csv")
            inference_csv = os.path.join(config[KEY_TEMPDIR],"inference_report.csv")
            constellation_list = get_voc_list(os.path.join(config[KEY_TEMPDIR], "get_constellations.txt"), config[KEY_ALIAS_FILE])

            generate_final_report(preprocessing_csv, inference_csv, config[KEY_ALIAS_FILE], constellation_list, config[KEY_PANGOLIN_DATA_VERSION],config[KEY_ANALYSIS_MODE], args.skip_designation_cache, config[KEY_OUTFILE],config)

            print(green(f"****\nOutput file written to: ") + config[KEY_OUTFILE])

            if config[KEY_ALIGNMENT_OUT]:
                print(green(f"****\nOutput alignment written to: ") + config[KEY_ALIGNMENT_FILE])


            return 0

        return 1
    return 1

if __name__ == '__main__':
    main()
