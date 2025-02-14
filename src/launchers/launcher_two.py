#!/usr/bin/python

""" Launches the sim_core with specific parameters

--------------------------
Created on Apr 4, 2017

@author: J. Sanchez-Garcia
"""

import sys
import json
import time
import subprocess
import logging
import settings
import sim_core
import client_socket
from subprocess import PIPE, Popen
from functions import timing
from functions import file_helper
from charts import avg_charts
from algorithms import lawn_mower


def launcher_create_scen(LAUNCH_CONFIG):

    logger = logging.getLogger(__name__)
    
    # Configuration flags
    # -------------------
    pso_flag = LAUNCH_CONFIG['pso']
    lawn_mower_flag = LAUNCH_CONFIG['lawn']
    exception_flag = LAUNCH_CONFIG['exception']
    pso_iterations = LAUNCH_CONFIG['pso_iter']
    lawn_iterations = LAUNCH_CONFIG['lawn_iter']
    
    t_start = time.time()
    
    # Generate lawn mower trajectories for defining the duration
    #-----------------------------------------------------------
    logger.info('Calculating the duration of the simulation from lawn_mower algo')
    
    CONFIG = settings.update_CONFIG()
    traj_per_drone = lawn_mower.gen_lawnmower_traj(CONFIG)
    settings.lm_trajectories = traj_per_drone
    
    duration = len(traj_per_drone[0])
    logger.info('Duration: '+str(duration))
    
    # Generate scenario
    #------------------
    # call to scenario_builder through socket
    logger.info('Using socket to get the scenario_builder generating the scenario')
    
    message = client_socket.get_scenario(duration)
    
    js_obj = json.loads(message)
    folder_path = js_obj['scenario']
    clusters = js_obj['clusters']
    settings.NODES_AMOUNT = js_obj['nodes_amount']
    
    folder = folder_path[-13:]
    relative_folder = './scenarios/'+folder+'/'
    command = ['mkdir',relative_folder]
    subprocess.call(command)
    
    # save new scenario from /scenario_builder folder to /scenario folder
    logger.info('Moving the new scenario to /scenarios folder')
    
    command = ['find',folder_path,'-maxdepth','1','-type','f']
    popen_proc = Popen(command,stdout=PIPE)
    files_to_copy = popen_proc.stdout.read()
    files_to_copy = files_to_copy.split('\n')
    del files_to_copy[-1]
    
    for file_i in files_to_copy:
        command = ['cp', file_i, relative_folder]
        subprocess.call(command)
    
    # get .wml filename
    logger.info('Finding the main .wml file')
    
    command = ['ls', relative_folder]
    popen_proc = Popen(command,stdout=PIPE)
    filename_l = popen_proc.stdout.read()
    
    # get '.wml' file name
    filename_l = filename_l.split('\n')
    for file_i in filename_l:
        if file_i.endswith('.wml'):
            wml_filename = file_i
        else:
            pass
    
    wml_full_path = relative_folder+wml_filename
    
    # save the scenario path in settings
    logger.info('Saving scenario path in settings file')
    settings.INPUT_FILE = wml_full_path
    
    CONFIG = settings.update_CONFIG()

    if CONFIG['f_duration'] == 0:
        settings.DURATION = duration
    else:
        # Leave the duration specified on the settings file
        pass
    
    settings.CLUSTERS = clusters
       
    #  SIM_CORE calls
    #-----------------
    
    timestamp_main = timing.timestamp_gen()
    logger.info('Creating output folder')
    
    main_output_folder = './outputs/'+str(timestamp_main)
    command = ['mkdir', main_output_folder]
    subprocess.call(command)
    
    settings.MAIN_OUTPUT_FOLDER = main_output_folder
    
    
    # PSO
    #-----
    if pso_flag == 1:
        
        
        pso_folder = main_output_folder+'/pso'
        command = ['mkdir', pso_folder]
        subprocess.call(command)
        
        settings.ALGORITHM = 'pso'
        
        for i in range(pso_iterations):   
            sub_timestamp = timing.timestamp_gen()
            sub_folder = pso_folder+'/'+str(sub_timestamp)
            command = ['mkdir', sub_folder]
            subprocess.call(command)
            
            settings.OUTPUT_FOLDER = sub_folder
            settings.CURRENT_ITERATION = i
            logger.info(str(settings.ALGORITHM)+' algorithm: iteration '+str(i))

            
            if exception_flag == 1:
                try:
                    logger.info('Calling sim_core')
                    sim_core.simulator()
                except (BaseException,KeyboardInterrupt):
                    logger.debug('pso iteration: '+str(i)+' -- Exception caught:' \
                                 +'\n\tfilename: '+sys.exc_info()[2].tb_frame.f_code.co_filename \
                                 +'\n\tlineno: '+str(sys.exc_info()[2].tb_lineno) \
                                 +'\n\tname: '+sys.exc_info()[2].tb_frame.f_code.co_name \
                                 +'\n\ttype: '+sys.exc_info()[0].__name__ \
                                 +'\n\tmessage: '+sys.exc_info()[1].message)

            else:
                logger.info('Calling sim_core')
                sim_core.simulator()

        
        #  Create averaged charts and maps
        #----------------------------------
        logger.info('Generating average charts for: '+settings.ALGORITHM)

        settings.TIMESTAMP =  timestamp_main # averaged charts will be generated with main timestamp
        CONFIG = settings.update_CONFIG()
        avg_charts.plot_all(settings.FILES, CONFIG)
        
        logger.info('Average charts generated for: '+settings.ALGORITHM)
    
    # Clean state after pso simulation
    settings.FILES = []
    
    # Lawn mower
    #------------
    if lawn_mower_flag == 1:
        lawn_folder = main_output_folder+'/lawn'
        command = ['mkdir', lawn_folder]
        subprocess.call(command)
        
        settings.ALGORITHM = 'lawn_mower'
        
        for i in range(lawn_iterations):   
            sub_timestamp = timing.timestamp_gen()
            sub_folder = lawn_folder+'/'+str(sub_timestamp)
            command = ['mkdir', sub_folder]
            subprocess.call(command)
            
            settings.OUTPUT_FOLDER = sub_folder
            settings.CURRENT_ITERATION = i
            logger.info(str(settings.ALGORITHM)+' algorithm: iteration '+str(i))

            if exception_flag == 1:
                try:
                    logger.info('Calling sim_core')
                    sim_core.simulator()
                except (BaseException,KeyboardInterrupt):
                    logger.debug('lawn_mower iteration: '+str(i)+' -- Exception caught:' \
                                 +'\n\tfilename: '+sys.exc_info()[2].tb_frame.f_code.co_filename \
                                 +'\n\tlineno: '+str(sys.exc_info()[2].tb_lineno) \
                                 +'\n\tname: '+sys.exc_info()[2].tb_frame.f_code.co_name \
                                 +'\n\ttype: '+sys.exc_info()[0].__name__ \
                                 +'\n\tmessage: '+sys.exc_info()[1].message)

            else:
                logger.info('Calling sim_core')
                sim_core.simulator()

        
        #  Create averaged charts and maps
        #-----------------------------------
        logger.info('Generating average charts for: '+settings.ALGORITHM)
        settings.TIMESTAMP =  timestamp_main # averaged charts will be generated with main timestamp
        CONFIG = settings.update_CONFIG()
        avg_charts.plot_all(settings.FILES, CONFIG)
        logger.info('Average charts generated for: '+settings.ALGORITHM)
    
    # Close files
    #-------------
    logger.info('All simulations terminated')
    
    t_end = time.time()
    sim_duration = (t_end - t_start) # simulation total duration 
    mins = int(sim_duration/60) # (minutes)
    secs = int(sim_duration%60)
    
    logger.info('Simulation duration: '+str(mins)+' mins '+str(secs)+' secs \n')




