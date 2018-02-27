#!/usr/bin/python3

import os
import sys
import argparse

from rtcFunctions import ImportHandler
from rtcFunctions import WorkspaceHandler
from rtcFunctions import RTCInitializer
from rtcFunctions import RTCLogin
from gitFunctions import Initializer, Differ
from gitFunctions import Commiter
from svnFunctions import svnCommiter
import configuration
import shouter


def initialize():
    config = configuration.get()
    directory = config.workDirectory
    if os.path.exists(directory):
        sys.exit("Configured directory already exists, please make sure to use a non-existing directory")
    shouter.shout("Migration will take place in " + directory)
    os.makedirs(directory)
    os.chdir(directory)
    config.deletelogfolder()

    RTCInitializer.initialize()

    # l'inizializzazione del repo bare la faccio dopo
    git = Initializer()
    git.initalize()
    if Differ.has_diff():
        git.initialcommit()
    Commiter.pushmaster()

def resume():

    # do not resume!
    shouter.shout("Resume disabled...Exit")
    exit(0)

    shouter.shout("Found existing git repo in work directory, resuming migration...")
    config = configuration.get()
    os.chdir(config.workDirectory)
    os.chdir(config.clonedGitRepoName)
    if Differ.has_diff():
        sys.exit("Your git repo has some uncommited changes, please add/remove them manually")
    RTCLogin.loginandcollectstreamuuid()
    Initializer.preparerepo()
    if config.previousstreamname:
        prepare()
    else:
        WorkspaceHandler().load()


def existsrepo():
    config = configuration.get()
    repodirectory = os.path.join(config.workDirectory, config.gitRepoName)
    return os.path.exists(repodirectory)


def migrate():
    rtc = ImportHandler()
    rtcworkspace = WorkspaceHandler()
    git = Commiter
    if existsrepo():
        resume()
    else:
        initialize()

    config = configuration.get()
    streamuuid = config.streamuuid
    streamname = config.streamname
    branchname = streamname + "_branchpoint"

    componentbaselineentries = rtc.getcomponentbaselineentriesfromstream(streamuuid)
    shouter.shout(" # componentbaselineentries:")
    for cbe in componentbaselineentries:
        shouter.shout(" # %s %s %s %s" % (cbe.componentname, cbe.component, cbe.baselinename, cbe.baseline))

    rtcworkspace.setnewflowtargets(streamuuid)

    history = rtc.readhistory(componentbaselineentries, streamname)
    # changeentries = rtc.getchangeentriesofstreamcomponents(componentbaselineentries)
    # if len(changeentries) > 0:
    #     git.branch(branchname)
    #     rtc.acceptchangesintoworkspace(rtc.getchangeentriestoaccept(changeentries, history))
    #     shouter.shout("All changes until creation of stream '%s' accepted" % streamname)
    #     git.pushbranch(branchname)

    #     rtcworkspace.setcomponentstobaseline(componentbaselineentries, streamuuid)
    #     rtcworkspace.load()

    # progressive compare between baselines
    # TODO: refactor this part into rtcFunctions.py
    if config.component2load:

        git.branch(branchname)  # Committer
        componentbaselines = rtc.getallcomponentbaselines(streamname, config.component2load)
        shouter.shout(" @ componentbaselines:")
        # debug only
        for i, cbl in enumerate(componentbaselines):
            shouter.shout(" @ %s %s %s %s" %
                          (cbl.componentname, cbl.component, cbl.baselinename, cbl.baseline))

        for i, cbl in enumerate(componentbaselines):
            missingchangeentries = {}
            if i < len(componentbaselines)-1:
                shouter.shout("Start collecting changeentries from Baseline(%s <%s>) to Baseline(%s <%s>):" %
                              (componentbaselines[i].baselinename, componentbaselines[i].baseline,
                               componentbaselines[i+1].baselinename, componentbaselines[i+1].baseline))
                changeentries = rtc.getchangeentriesbetweenbaselines(
                    componentbaselines[i].baseline, componentbaselines[i+1].baseline)
                for changeentry in changeentries:
                    missingchangeentries[changeentry.revision] = changeentry

            if len(missingchangeentries):
                shouter.shout("Accepting collected changesets [%s-%s]" %
                    (componentbaselines[i].baselinename, componentbaselines[i+1].baselinename))
                rtc.acceptchangesintoworkspace(rtc.getchangeentriestoaccept(missingchangeentries, history))
                shouter.shout("/*\/*\/*\ All changes until baseline '%s' accepted" % componentbaselines[i+1].baselinename)

                # Set tag only if there are changesets between baselines
                git.settagname(componentbaselines[i+1].baselinename)
#                print("svn repo dir = %s" % config.svnrepodir)
#                if config.svnrepodir and config.svnrepodir.strip(" ") != '':
#                    svn.settagname(componentbaselines[i+1].baselinename)
        git.pushbranch(branchname)

    git.branch(streamname)
    changeentries = rtc.getchangeentriesofstream(streamuuid)
    amountofacceptedchanges = rtc.acceptchangesintoworkspace(rtc.getchangeentriestoaccept(changeentries, history))
    if amountofacceptedchanges > 0:
        git.pushbranch(streamname)
        git.promotebranchtomaster(streamname)

    RTCLogin.logout()
    summary(streamname)


def prepare():
    config = configuration.get()
    rtc = ImportHandler()
    rtcworkspace = WorkspaceHandler()
    # git checkout branchpoint
    Commiter.checkout(config.previousstreamname + "_branchpoint")
    # list baselines of current workspace
    componentbaselineentries = rtc.getcomponentbaselineentriesfromstream(config.previousstreamuuid)
    # set components to that baselines
    rtcworkspace.setcomponentstobaseline(componentbaselineentries, config.previousstreamuuid)
    rtcworkspace.load()


def summary(streamname):
    config = configuration.get()
    shouter.shout("\nAll changes accepted - Migration of stream '%s' is completed."
                  "\nYou can distribute the git-repo '%s'." % (streamname, config.gitRepoName))
    if len(config.ignorefileextensions) > 0:
        # determine and log the ignored but still present files
        os.chdir(config.workDirectory)
        os.chdir(config.clonedGitRepoName)
        pathtoclonedgitrepo = config.workDirectory + os.sep + config.clonedGitRepoName
        if pathtoclonedgitrepo[-1:] != os.sep:
            pathtoclonedgitrepo += os.sep
        ignoredbutexist = []
        with open('.gitignore', 'r') as gitignore:
            for line in gitignore.readlines():
                line = line.strip()
                if line != ".jazz5" and line != ".metadata" and line != ".jazzShed":
                    pathtoignored = pathtoclonedgitrepo + line
                    if os.path.exists(pathtoignored):
                        ignoredbutexist.append(line)
        if len(ignoredbutexist) > 0:
            shouter.shout("\nThe following files have been ignored in the new git repository, " +
                          "but still exist in the actual RTC workspace:")
            ignoredbutexist.sort()
            for ignored in ignoredbutexist:
                shouter.shout("\t" + ignored)


def parsecommandline():
    parser = argparse.ArgumentParser()
    configfiledefault = 'config.ini'
    configfilehelp = 'name of the config file, or full path to the config file; defaults to ' + configfiledefault
    parser.add_argument('-c', '--configfile', metavar='file', dest='configfile', help=configfilehelp,
                        default=configfiledefault)
    parser.add_argument('-u', '--user', metavar='user', dest='user', help='RTC user', default=None)
    parser.add_argument('-p', '--password', metavar='password', dest='password', help='RTC password', default=None)
    arguments = parser.parse_args()
    configuration.setconfigfile(arguments.configfile)
    configuration.setUser(arguments.user)
    configuration.setPassword(arguments.password)


def validate():
    config = configuration.get()
    streamname = config.streamname
    branchname = streamname + "_branchpoint"
    previousstreamname = config.previousstreamname
    offendingbranchname = None
    if not Commiter.checkbranchname(streamname):
        offendingbranchname = streamname
    elif not Commiter.checkbranchname(branchname):
        offendingbranchname = branchname
    elif not Commiter.checkbranchname(previousstreamname):
        offendingbranchname = previousstreamname
    if offendingbranchname:
        sys.exit(offendingbranchname + " is not a valid git branch name - consider renaming the stream")


if __name__ == "__main__":
    parsecommandline()
    validate()
    migrate()
