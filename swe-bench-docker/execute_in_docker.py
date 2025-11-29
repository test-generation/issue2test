import docker
import os
import io
import tarfile
import argparse
import subprocess

build_logs_dir = "build_files"

from docker.errors import APIError, ImageNotFound, DockerException

def pull_image(client, image_name):
    print(f"Pulling Docker image '{image_name}'...")
    try:
        client.images.pull(image_name)
        print(f"Image '{image_name}' pulled successfully.")
        return 0
    except ImageNotFound:
        print(f"Error: The image '{image_name}' was not found.")
        return 1
    except APIError as api_error:
        print(f"Error: Unable to pull the image '{image_name}'. Check your internet connection or Docker configuration.")
        print(f"Details: {api_error}")
        return 2
    except DockerException as docker_exception:
        print(f"Docker error: {docker_exception}")
        return 3
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return 4


def start_container(client, image_name):
    print(f"Starting container from image '{image_name}'...")
    container = client.containers.run(image_name, detach=True)
    print(f"Container '{container.id[:12]}' started.")
    return container

def create_tar(file_path, arcname):
    file_like_object = io.BytesIO()
    with tarfile.open(fileobj=file_like_object, mode='w') as tar:
        tar.add(file_path, arcname=arcname)
    file_like_object.seek(0)
    return file_like_object

def copy_files_to_container(container, files_to_copy, test_folders, instance_id):
    """
    :param container: Docker container object.
    :param folder_path: Path to the folder
    """
    paths_lst_path = files_to_copy
    with open(test_folders) as tfd:
    	proj_test_path = dict([l.split(" ") for l in tfd.read().splitlines()])
    	
    if not os.path.exists(paths_lst_path):
        raise FileNotFoundError(f"files_to_copy: path not found {files_to_copy}")
    
    with open(paths_lst_path, "r") as file:
        lines = file.readlines()

    eval_path = "build_files/INSTANCE_ID/eval.sh#/testbed/eval.sh".replace("INSTANCE_ID", instance_id)
    diff_path = "build_files/INSTANCE_ID/patch.diff#/testbed/patch.diff".replace("INSTANCE_ID", instance_id)

    lines = [eval_path, diff_path] + lines
    for k in proj_test_path:
        if k in instance_id:
            test_path = proj_test_path[k]
    
    for line in lines:
        source_file, dest_path = line.strip().replace("\n", "").split("#")
        source_file_path = os.path.join(source_file)
        
        dest_path = os.path.join(test_path, dest_path)
        
        if not os.path.exists(source_file_path):
            raise FileNotFoundError(f"File {source_file} not found in ...")
        
        # Make the source file into a tar archive for copying
        tar_stream = create_tar(source_file_path, os.path.basename(dest_path))
        
        # Extract the tar archive into the desired destination inside the container
        print(f"Copying {source_file_path} to {dest_path} inside the container...")
        container.put_archive(os.path.join("/testbed", os.path.dirname(dest_path)), tar_stream.getvalue())

def parse_file_pairs(file_path):
    file_pairs = []
    with open(file_path, 'r') as file:
        for line in file:
            local_path, container_path = line.strip().split("#")
            file_pairs.append((local_path, container_path))
    return file_pairs

def run_script_in_container(container, script_path="/testbed/eval.sh"):
    print(f"Executing '{script_path}' in container...")
    exec_log = container.exec_run(f"bash {script_path}")
    output = exec_log.output.decode("utf-8")
    #print(f"Execution result:\n{output}")
    return output

def update_command_with_paths(eval_script_path, paths_lst_path, instance_id):
    """
    Update the test command in the eval.sh script by replacing file paths with those from the paths.lst file,
    based on the context provided by the lines before and after the command.

    :param eval_script_path: Path to the eval.sh script.
    :param paths_lst_path: Path to the paths.lst file.
    """
    # Read the paths from the paths.lst file
    with open(paths_lst_path, 'r') as paths_file:
        path_mappings = [line.replace("\n", "").split("#") for line in paths_file.readlines()]

    # Extract only the PATH_IN_FOLDER parts
    if "django" in instance_id:
    	new_paths = [mapping[1].replace("/", ".").replace('.py', '') for mapping in path_mappings]
    	print("MAPPING:", path_mappings)
    	print("NEW_PATHS:", new_paths)
    else:
        new_paths = [mapping[1] for mapping in path_mappings]
    # Read the eval.sh script
    with open(eval_script_path, 'r') as script_file:
        script_content = script_file.readlines()

    # Define the markers to identify the command
    before_marker = "EOF_"  # Line before the command
    after_marker = "git checkout"  # Line after the command

    updated_content = []
    inside_command_block = False

    for i, line in enumerate(script_content):
        if before_marker in line:
            updated_content.append(line)
            inside_command_block = True
        elif inside_command_block and after_marker in line:
            # Replace the paths in the command
            previous_command = script_content[i-1]
            command_parts = previous_command.split()
            for cp in command_parts[::-1]:
                if "." in cp or "/" in cp:
                    command_parts = command_parts[:-1]
                else:
                    break
            # Replace file paths with new paths
            new_command = ' '.join(command_parts) + ' ' + ' '.join(new_paths) + '\n'
            updated_content[-1] = new_command
            updated_content.append(line)
            inside_command_block = False
        else:
            updated_content.append(line)

    # Write the updated content back to the eval.sh script
    with open(eval_script_path, 'w') as script_file:
        script_file.writelines(updated_content)
    
    print(f"Updated command in {eval_script_path} with new paths from {paths_lst_path}.")

def add_patch_command_to_eval_script(eval_script_path, R=False):
    """
    Adds the 'patch -p1 < patch.diff' command before the pytest line in eval.sh.
    """
    with open(eval_script_path, 'r') as file:
        f_content = file.read()

    with open(eval_script_path, 'w') as file:
        file.write(f_content.replace("patch -p1  <", "echo ").replace("patch -p1 -R", "echo "))

    with open(eval_script_path, 'r') as file:
        lines = file.readlines()

    # Find the pytest line and insert the patch command before it
    for i, line in enumerate(lines):
        if line.startswith("git diff"):
            print("INSERTED PATCH LINE")
            r = ""
            if R:
                r = "-R"
            lines.insert(i+1, 'patch -p1 {} < patch.diff\n'.format(r))
            break
    
    # Write the modified lines back to eval.sh
    with open(eval_script_path, 'w') as file:
        file.writelines(lines)

def main(image_name, test_paths, file_pairs_path, instance_id, is_fixed):
    client = docker.from_env()

    # Step 1: Pull the Docker image
    pull_code = pull_image(client, image_name)
    if pull_code != 0:
        print("Failed to pull remote image.")
        print("Building locally...")
        if not os.path.exists(os.path.join("build_files", instance_id)):
            command = [
                    "python", "-m", "swebench.harness.run_evaluation",
                    "--predictions_path", "gold",
                    "--max_workers", "1",
                    "--instance_ids", instance_id,
                    "--run_id", "validate-gold"
                ]
            subprocess.run(command, check=True)
        else:
            print("Instance already processed, skipping build...")
        container_name="sweb.eval.{}.validate-gold".format(instance_id)
        os.system("docker commit {} {}".format(container_name, image_name))

        os.system("cp -r logs/run_evaluation/validate-gold/gold/{} {}/".format(instance_id, build_logs_dir))
        os.system("rm -rf logs")
        #TODO: build locally
    # Step 2: Start the Docker container
    container = start_container(client, image_name)

    
    
    if os.path.exists("{}/{}/eval.sh.temp".format(build_logs_dir, instance_id)):
        temp_eval_script_path = "{}/{}/eval.sh.temp".format(build_logs_dir, instance_id)
        with open(temp_eval_script_path, 'r') as file:
            f_content = file.read()

        with open(temp_eval_script_path, 'w') as file:
            file.write(f_content.replace("patch -p1  <", "echo ").replace("patch -p1 -R", "echo "))

        os.system("cp {}/{}/eval.sh.temp {}/{}/eval.sh".format(build_logs_dir, instance_id, build_logs_dir, instance_id))
    else:
        os.system("cp {}/{}/eval.sh {}/{}/eval.sh.temp".format(build_logs_dir, instance_id, build_logs_dir, instance_id))    
    update_command_with_paths("{}/{}/eval.sh".format(build_logs_dir, instance_id), test_paths, instance_id)
    if is_fixed:
        add_patch_command_to_eval_script("{}/{}/eval.sh".format(build_logs_dir, instance_id))
    else:
        add_patch_command_to_eval_script("{}/{}/eval.sh".format(build_logs_dir, instance_id), R=True)
    # Step 3: Read file pairs and copy files
    file_pairs = parse_file_pairs(file_pairs_path)
    copy_files_to_container(container, files_to_copy, test_folders, instance_id)

    # Step 4: Run eval.sh in the container
    container.exec_run("chmod +x /testbed/eval.sh")
    result = run_script_in_container(container)


    # Cleanup: Stop and remove the container
    print("Cleaning up: stopping and removing the container.")
    container.stop()
    container.remove()
    
    return result

def validate_input_files(files_to_copy, test_paths, test_folders, instance_id):
    # Check if each required file exists
    if not os.path.exists(files_to_copy):
        raise FileNotFoundError(f"Error: '{files_to_copy}' file is missing.")
    if not os.path.exists(test_paths):
        raise FileNotFoundError(f"Error: '{test_paths}' file is missing.")
    if not os.path.exists(test_folders):
        raise FileNotFoundError(f"Error: '{test_folders}' file is missing.")

    # Validate 'files_to_copy' structure
    with open(files_to_copy, 'r') as f:
        lines = f.readlines()
        #if len(lines) < 2:
        #    raise ValueError(f"Error: '{files_to_copy}' must contain at least two lines.")
        #if "INSTANCE_ID" in lines[0] or "INSTANCE_ID" in lines[1]:
        #    print("FILE CONTENT NOT ALLOWED---------------------------")
        #    print(lines)
        #    raise ValueError(f"Error: '{files_to_copy}' has placeholders that need to be replaced with actual issue_id.")
        for line in lines:
            if "#" not in line or len(line.strip().split("#")) != 2:
                print("FILE CONTENT NOT ALLOWED---------------------------")
                print(line)
                raise ValueError(f"Error: Each line in '{files_to_copy}' must contain exactly one '#' separating the source and destination paths.")
    
    # Validate 'test_paths' structure
    with open(test_paths, 'r') as f:
        lines = f.readlines()
        if len(lines) == 0 or lines[0] in ["", "\n", " "]:
            raise ValueError("Test paths should contain at least one valid test paths path_to_file_on_host#path_to_file_in_container")
        for line in f:
            if "#" not in line or len(line.strip().split("#")) != 2:
                print("FILE CONTENT NOT ALLOWED---------------------------")
                print(line)
                raise ValueError(f"Error: Each line in '{test_paths}' must contain exactly one '#' separating the source and destination paths.")
    
    # Validate 'test_folders' structure and check for the instance-specific path
    found_instance_path = False
    with open(test_folders, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 2:
                raise ValueError(f"Error: Each line in '{test_folders}' must contain exactly two elements separated by space (project name and test folder path).")
            if parts[0] in instance_id:
                found_instance_path = True
    if not found_instance_path:
        raise ValueError(f"Error: '{test_folders}' does not contain a valid path mapping for the instance '{instance_id}'.")

    print("All input files are valid and meet the required constraints.")

# Run the main function
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("instance_id", help="Instance id of and issue, e.g, django__django-14752")
    parser.add_argument("test_paths", help="A file containing pairs of (test file paths or names on the host machine, paths/names inside the docker)")
    parser.add_argument("files_to_copy", help="A file containing the list of all files that should be copied from the host machine to the docker container (including generated test files)")
    parser.add_argument("test_folders", help="A file containing pairs of (project name, deault parent test folder, e.g, 'django /testbed/tests')")
    parser.add_argument("--fixed", action= "store_true", help="Using this argument to run test on fixed version")
    args = parser.parse_args()
    instance_id = args.instance_id
    test_paths = args.test_paths
    files_to_copy = args.files_to_copy
    test_folders = args.test_folders
    is_fixed = args.fixed

    validate_input_files(files_to_copy, test_paths, test_folders, instance_id)

    image_name = "islemdockerdev/{}".format(instance_id.replace("-", "").replace("_", "")) 
    output = main(image_name, test_paths, files_to_copy, instance_id, is_fixed)
    
    with open("{}_raw_output".format(instance_id) + ("_fixed" if is_fixed else "_buggy"), "w") as rot:
        rot.write(output)

    try:
        print("Test Execution finished with the following output:")
        trim = """ cleanly.\n"""
        print(output[output.find(trim) + len(trim):])
        with open("{}_test_results".format(instance_id)+ ("_fixed" if is_fixed else "_buggy"), "w") as tsr:
            tsr.write(output[output.find(trim) + len(trim):])
        
    except Exception as e:
        print(f"An error occurred while trying to execute tests: {e}")

    ## Restore input files to default values to avoid issues
    with open("files_to_copy", "w") as ftc:
        ftc.write("""build_files/INSTANCE_ID/eval.sh#/testbed/eval.sh\nbuild_files/INSTANCE_ID/patch.diff#/testbed/patch.diff""")


    with open("test_paths", "w") as tph:
        tph.write("")
