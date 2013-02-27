import StringIO
import util


def test_read_history():
    contents = '''CompletionDate = 1361297173
EnteredCurrentStatus = 1361297000
StartdPrincipal = "unauthenticated@unmapped/192.168.1.110"
EnteredCurrentStatus = 1361297172
TerminationPending = true
*** Offset = -1 ClusterId = 3 ProcId = 7 Owner = "name" CompletionDate = 1361297173
LeaveJobInQueue = false
EnteredCurrentStatus = 1361298176
ExitCode = 0
ClusterId = 3
CompletionDate = 1361298177
*** Offset = -1 ClusterId = 3 ProcId = 9 Owner = "name" CompletionDate = 1361298177
'''

    # this is at the end so there is nothing to read
    file = StringIO.StringIO(contents)
    ads = list(util.readCondorHistory(file, 1361298177))
    assert len(ads) == 0

    # this is before the last one
    ads = list(util.readCondorHistory(file, 1361298176))
    assert len(ads) == 1

    # this matches the first one so it only includes the last
    ads = list(util.readCondorHistory(file, 1361297173))
    assert len(ads) == 1
    assert set(["LeaveJobInQueue", "EnteredCurrentStatus", "CompletionDate", "ExitCode", "ClusterId"]) == set(ads[0].ad.keys())
    assert "1361298176" == ads[0].ad["EnteredCurrentStatus"]

    # this matches all
    ads = list(util.readCondorHistory(file, 0))
    assert len(ads) == 2
    assert set(["CompletionDate", "EnteredCurrentStatus", "StartdPrincipal", "TerminationPending"]) == set(ads[1].ad.keys())
    assert set(["LeaveJobInQueue", "EnteredCurrentStatus", "CompletionDate", "ExitCode", "ClusterId"]) == set(ads[0].ad.keys())
    # make sure we use the LAST EnteredCurrentStatus (it appears twice in each job in history files)
    assert "1361297172" == ads[1].ad["EnteredCurrentStatus"]

    # simplify this since the ordering can vary
    del ads[1].ad["TerminationPending"]
    del ads[1].ad["CompletionDate"]
    del ads[1].ad["EnteredCurrentStatus"]
    assert 'StartdPrincipal = "unauthenticated@unmapped/192.168.1.110"' == ads[1].get_text()


def test_skip_invalid():
    '''Tests ability to handle incomplete jobs put in by the SOAP API. 
    In this case, EnteredCurrentStatus is very early (and in fact all the 
    times can be equally early).
    '''

    # note the first job is a poison job--it wouldn't appear in real life,
    # but it's here to make sure we don't read too far
    contents = '''CompletionDate = 19000
EnteredCurrentStatus = 19000
ProcId = 4
*** Offset = -1 ClusterId = 1 ProcId = 2 Owner = "name" CompletionDate = 19000
CompletionDate = 10000
EnteredCurrentStatus = 10000
ProcId = 2
*** Offset = -1 ClusterId = 1 ProcId = 2 Owner = "name" CompletionDate = 10000
CompletionDate = 0
EnteredCurrentStatus = 8000
ProcId = 1
*** Offset = -1 ClusterId = 1 ProcId = 1 Owner = "name" CompletionDate = 0
CompletionDate = 20000
EnteredCurrentStatus = 20000
ProcId = 3
*** Offset = -1 ClusterId = 1 ProcId = 3 Owner = "name" CompletionDate = 20000
'''
                                                                                 
    file = StringIO.StringIO(contents)
    ads = list(util.readCondorHistory(file, 20000))
    assert len(ads) == 0
    
    # if we read the 20000 job, we have to also read the 8000 job,
    # even though 8000 < 17000, because 8000 measures possibly
    # the start of the job, not the end. But we don't have to read the 10000.
    ads = list(util.readCondorHistory(file, 17000))
    assert len(ads) == 2
    
    # this requires us to read the whole way, including the false job at the start
    ads = list(util.readCondorHistory(file, 9000))
    assert len(ads) == 4

    
import sys

if __name__ == "__main__":
    files = list(util.readCondorHistory(file(sys.argv[1], "rb"), int(sys.argv[2])))
    jobs = []
    for ad in reversed(files):
        jobs.append(ad.get_text())
        
    print "\n".join(jobs)



