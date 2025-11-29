import os


iteration_folder = "generated-tests/iteration-3"
instances = os.listdir(iteration_folder)


for instance in instances:
    try:
        new_paths_lst = []
        with open(os.path.join(iteration_folder, instance, "generated_tests", "paths.lst")) as pathsf:
            paths_lst = pathsf.readlines()

        for path in paths_lst:
            new_paths_lst.append(
                os.path.join(iteration_folder, instance, "generated_tests", path.split(" ")[0]) + "#" + path.replace(path.split(" ")[0]+" " , "")
                )
        
        os.system("mkdir -p prepared_files/{}".format(instance))

        with open(os.path.join("prepared_files", instance, "test_paths"), "w") as pft:
            pft.writelines(new_paths_lst)

        template_copy = """build_files/INSTANCE_ID/eval.sh#/testbed/eval.sh\nbuild_files/INSTANCE_ID/patch.diff#/testbed/patch.diff"""

        template_copy = template_copy.replace("INSTANCE_ID", instance)

        with open(os.path.join("prepared_files", instance, "files_to_copy"), "w") as pif:
            pif.write(template_copy+"\n"+"\n".join(new_paths_lst))

    except Exception as e:
        print("An error occured while trying to prepare files for instance {}".format(instance))
        print("The error message: " + str(e))