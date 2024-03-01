def TimeStepInput():
    """Prompt the user to choose a time step, in hours, to split the data. 

    Returns:
        integer : returns the Time step from chosen by the user.
    """    """"""      
    time_step = input("Enter the value of your time step (in hours): ")     
    return time_step
  
def PathInput():
    """Prompt the user to give the path of the UVP6 project where all the data.txt to merge/split can be found.

    Returns:
        string : A string of the absolute path given by the user
    """    
    path_input = input("Enter the path of the folder where the data.txt to merged are stored: ")
    return path_input

def StartInput():
    """Prompt the user to give the date time of when the split/merge should start.

    Returns:
        string : A string in the format %Y%m%d-%H%M%S
    """    
    start_input = input("At which day time do you want to start the split ? ('%Y%m%d-%H%M%S' format) ")
    return start_input

def StepInput():
    """Prompt the user to choose a time step, in hours, to split the data. 

    Returns:
        integer : returns the Time step from chosen by the user.
    """    
    step_input = input("What's the time step of the split ? (in hours) ")
    return step_input

def PathOutput():
    """Prompt the user to choose a path to save the results.

    Returns:
        strings : An absolute path where all the files will be saved in a UVP6 project structure.
    """    
    output_folder = input("Where do you want to store the output data ? ")
    return output_folder
