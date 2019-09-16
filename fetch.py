import logging
import requests
import ConfigParser


def get_job_json(url, job_name):
    return requests.get(
        "%s/job/%s/api/json" % (
            url,
            job_name,
        ),
    ).json()


def get_build_json(url, job_name, build_num):
    return requests.get(
        "%s/job/%s/%s/api/json" % (
            url,
            job_name,
            build_num,
        ),
    ).json()


def main():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("main")
    jobs = dict()
    jenkins_config = ConfigParser.ConfigParser()
    job_config = ConfigParser.ConfigParser()
    executor_jenkins_data = ConfigParser.ConfigParser()

    log.info("Reading jenkins and jobs config files")
    jenkins_config.read("jenkins.cfg")
    job_config.read("jobs.cfg")

    jenkins_url = jenkins_config.get("URL", "jenkins")
    executor_job = jenkins_config.get("JOBS", "executor")
    target_build = jenkins_config.get("JOBS", "build")
    components = job_config.sections()

    executor_jenkins_data.read(executor_job + "_cache.dat")
    for component in components:
        jobs[component] = dict()
        subcomponents = job_config.items(component)
        for subcomponent in subcomponents:
            jobs[component][subcomponent[0]] = dict()
            jobs[component][subcomponent[0]]["RUN_STATUS"] = "NA"
            jobs[component][subcomponent[0]]["TOTAL"] = subcomponent[1]
            jobs[component][subcomponent[0]]["PASSED"] = 0

    log.info("Fetching executor jobs. This might take few minutes...")
    executor_json = get_job_json(jenkins_url, executor_job)
    executor_builds= executor_json["builds"]
    for build in executor_builds:
        found_in_cache = False
        build_num = build["number"]
        if str(build_num) in executor_jenkins_data.sections():
            t_build_num = str(build_num)
            log.debug("Build %s found in cache" % build_num)
            found_in_cache = True
            build_data = dict()
            build_data["building"] = False
            build_data["result"] = executor_jenkins_data.get(t_build_num, "RUN_STATUS")
            description = executor_jenkins_data.get(t_build_num, "DESCRIPTION").split(" ")
        else:
            log.debug("Fetching build: %s" % build["number"])
            build_data = get_build_json(jenkins_url, executor_job, build_num)
            description = build_data["description"].split(" ")

        component = str(description[2])
        subcomponent = str(description[3]).lower()
        build_num = description[0]

        log.debug("Component: %s, subcomponent: %s, description: %s"
                  % (component, subcomponent, description))
        
        result = [0, 0]
        if build_data["building"]:
            run_status = "RUNNING"
        else:
            run_status = build_data["result"]
            if len(description) > 6:
                result = str(description[6])[1:len(description[6])-1].split("/")
        
        log.debug("Build run_status: %s, %s" % (run_status, result))

        if run_status != "RUNNING" and not found_in_cache:
            tem_b_num = str(build["number"])
            executor_jenkins_data.add_section(tem_b_num)
            executor_jenkins_data.set(
                tem_b_num,
                "RUN_STATUS",
                run_status)
            executor_jenkins_data.set(
                tem_b_num,
                "DESCRIPTION",
                build_data["description"])

        if build_num == target_build \
                and component in components \
                and subcomponent in jobs[component].keys() \
                and jobs[component][subcomponent]["RUN_STATUS"] == "NA":
            jobs[component][subcomponent]["RUN_STATUS"] = run_status
            jobs[component][subcomponent]["PASSED"] = int(result[0])
            log.debug("Updated result %s / %s, total_ran: %s"
                      % (result[0], result[1], result[1]))
            
    log.info("Saving jenkins executor results in cache")
    with open(executor_job + "_cache.dat", "w") as data_file:
        executor_jenkins_data.write(data_file)

    log.info("Preparing report..")
    total_cases = 0
    passed_cases = 0
    csv_file = open("data/report_%s.csv" % target_build, "w")
    csv_file.write("Status,Job,Total,Passed\n")
    for component in jobs.keys():
        log.info("Component %s" % component)
        for subcomponent in jobs[component].keys():
            csv_file.write("%s,%s,%s,%s\n"
                           % (jobs[component][subcomponent]["RUN_STATUS"],
                              subcomponent,
                              jobs[component][subcomponent]["TOTAL"],
                              jobs[component][subcomponent]["PASSED"]))
            log.info("%8s %s %s" % (jobs[component][subcomponent]["RUN_STATUS"],
                                    subcomponent,
                                    jobs[component][subcomponent]["PASSED"]))
            passed_cases += int(jobs[component][subcomponent]["PASSED"])
            total_cases += int(jobs[component][subcomponent]["TOTAL"])

    csv_file.close()
    pass_percentage = (100 * passed_cases) / total_cases
    log.info("Total: %s" % total_cases)
    log.info("Passed: %s, %2f%%" % (passed_cases, pass_percentage))
        

if __name__ == "__main__":
    main()
