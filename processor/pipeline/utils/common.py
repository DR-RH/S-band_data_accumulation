
def get_save_directory_name(path):
    directory_name = path.split('/')[-1]
    directory_name = directory_name.split(".txt")[0]
    return directory_name