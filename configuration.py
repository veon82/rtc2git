import os
import configparser
import shutil
import shlex

import shell
import shouter

config = None
configfile = None
user = None
password = None


def read(configname=None):
    if not configname:
        global configfile
        configname = configfile
    parsedconfig = configparser.ConfigParser()
    if len(parsedconfig.read(configname)) < 1:
        raise IOError('unable to read %s' % configname)
    generalsection = parsedconfig['General']
    migrationsectionname = 'Migration'
    migrationsection = parsedconfig[migrationsectionname]
    miscsectionname = 'Miscellaneous'
    global user
    if not user:
        user = generalsection['User']
    global password
    if not password:
        password = generalsection['Password']
    repositoryurl = generalsection['Repo']
    scmcommand = generalsection.get('ScmCommand', "lscm")
    shell.logcommands = parsedconfig.get(miscsectionname, 'LogShellCommands', fallback="False") == "True"
    shell.setencoding(generalsection.get('encoding'))

    workspace = shlex.quote(generalsection['WorkspaceName'])
    gitreponame = generalsection['GIT-Reponame']
    svnrepodir = shlex.quote(generalsection['SVNRepoDir'])

    useexistingworkspace = generalsection.get('useExistingWorkspace', "False")
    useprovidedhistory = migrationsection.get('UseProvidedHistory', "False")
    useautomaticconflictresolution = migrationsection.get('UseAutomaticConflictResolution', "False")
    maxchangesetstoaccepttogether = migrationsection.get('MaxChangeSetsToAcceptTogether', "10")

    workdirectory = generalsection.get('Directory', os.getcwd())
    streamname = shlex.quote(migrationsection['StreamToMigrate'].strip())
    previousstreamname = migrationsection.get('PreviousStream', '').strip()

    # new option
    component2load = shlex.quote(migrationsection['component2Load'].strip())

    baselines = getinitialcomponentbaselines(migrationsection.get('InitialBaseLines'))
    ignorefileextensionsproperty = parsedconfig.get(miscsectionname, 'IgnoreFileExtensions', fallback='')
    ignorefileextensions = parsesplittedproperty(ignorefileextensionsproperty)
    ignoredirectoriessproperty = parsedconfig.get(miscsectionname, 'IgnoreDirectories', fallback='')
    ignoredirectories = parsesplittedproperty(ignoredirectoriessproperty)
    includecomponentroots = parsedconfig.get(miscsectionname, 'IncludeComponentRoots', fallback="False")
    commitmessageprefix = migrationsection.get('CommitMessageWorkItemPrefix', "")
    gitattributesproperty = parsedconfig.get(migrationsectionname, 'Gitattributes', fallback='')
    gitattributes = parsesplittedproperty(gitattributesproperty)

    configbuilder = Builder().setuser(user).setpassword(password).setrepourl(repositoryurl).setscmcommand(scmcommand)
    configbuilder.setworkspace(workspace).setgitreponame(gitreponame).setrootfolder(os.getcwd())
    configbuilder.setuseexistingworkspace(useexistingworkspace).setuseprovidedhistory(useprovidedhistory)
    configbuilder.setuseautomaticconflictresolution(useautomaticconflictresolution)
    configbuilder.setmaxchangesetstoaccepttogether(maxchangesetstoaccepttogether)
    configbuilder.setworkdirectory(workdirectory).setstreamname(streamname).setinitialcomponentbaselines(baselines)
    configbuilder.setpreviousstreamname(previousstreamname)
    configbuilder.setcomponent2load(component2load)
    configbuilder.setignorefileextensions(ignorefileextensions)
    configbuilder.setignoredirectories(ignoredirectories)
    configbuilder.setincludecomponentroots(includecomponentroots).setcommitmessageprefix(commitmessageprefix)
    configbuilder.setgitattributes(gitattributes)
    configbuilder.setsvnrepodir(svnrepodir)
    global config
    config = configbuilder.build()
    return config


def get():
    if not config:
        read()
    return config


def setconfigfile(newconfigfile):
    global configfile
    configfile = newconfigfile


def setUser(newuser):
    global user
    user = newuser


def setPassword(newpassword):
    global password
    password = newpassword


def getinitialcomponentbaselines(definedbaselines):
    initialcomponentbaselines = []
    if definedbaselines:
        componentbaselines = definedbaselines.split(",")
        for entry in componentbaselines:
            componentbaseline = entry.split("=")
            component = componentbaseline[0].strip()
            baseline = componentbaseline[1].strip()
            initialcomponentbaselines.append(ComponentBaseLineEntry(component, baseline, component, baseline))
    return initialcomponentbaselines


def parsesplittedproperty(property, separator=';'):
    """
    :param property
    :return: a list single properties, possibly empty
    """
    properties = []
    if property and len(property) > 0:
        for splittedproperty in property.split(separator):
            properties.append(splittedproperty.strip())
    return properties


class Builder:
    def __init__(self):
        self.user = ""
        self.password = ""
        self.repourl = ""
        self.scmcommand = "lscm"
        self.workspace = ""
        self.useexistingworkspace = ""
        self.useprovidedhistory = ""
        self.useautomaticconflictresolution = ""
        self.maxchangesetstoaccepttogether = ""
        self.workdirectory = os.path.dirname(os.path.realpath(__file__))
        self.rootFolder = self.workdirectory
        self.logFolder = self.rootFolder + os.sep + "Logs"
        self.hasCreatedLogFolder = os.path.exists(self.logFolder)
        self.initialcomponentbaselines = ""
        self.streamname = ""
        self.gitreponame = ""
        self.clonedgitreponame = ""
        self.previousstreamname = ""
        self.ignorefileextensions = ""
        self.ignoredirectories = ""
        self.includecomponentroots = ""
        self.commitmessageprefix = ""
        self.gitattributes = ""
        self.component2load = ""
        self.svnrepodir = ""

    def setuser(self, user):
        self.user = user
        return self

    def setpassword(self, password):
        self.password = password
        return self

    def setrepourl(self, repourl):
        self.repourl = repourl
        return self

    def setscmcommand(self, scmcommand):
        self.scmcommand = scmcommand
        return self

    def setworkspace(self, workspace):
        self.workspace = workspace
        return self

    def setsvnrepodir(self, svnrepodir):
        self.svnrepodir = svnrepodir
        return self

    def setworkdirectory(self, workdirectory):
        self.workdirectory = workdirectory
        return self

    def setrootfolder(self, rootfolder):
        self.rootFolder = rootfolder
        return self

    def setlogfolder(self, logfolder):
        self.logFolder = logfolder
        return self

    def setinitialcomponentbaselines(self, initialcomponentbaselines):
        self.initialcomponentbaselines = initialcomponentbaselines
        return self

    def setstreamname(self, streamname):
        self.streamname = streamname
        return self

    def setcomponent2load(self, component2load):
        self.component2load = component2load
        return self

    def setgitreponame(self, reponame):
        self.gitreponame = reponame
        self.clonedgitreponame = reponame[:-4]  # cut .git
        return self

    def setuseexistingworkspace(self, useexistingworkspace):
        self.useexistingworkspace = self.isenabled(useexistingworkspace)
        return self

    def setuseprovidedhistory(self, useprovidedhistory):
        self.useprovidedhistory = self.isenabled(useprovidedhistory)
        return self

    def setuseautomaticconflictresolution(self, useautomaticconflictresolution):
        self.useautomaticconflictresolution = self.isenabled(useautomaticconflictresolution)
        return self

    def setmaxchangesetstoaccepttogether(self, maxchangesetstoaccepttogether):
        self.maxchangesetstoaccepttogether = int(maxchangesetstoaccepttogether)
        return self

    def setpreviousstreamname(self, previousstreamname):
        self.previousstreamname = previousstreamname
        return self

    def setignorefileextensions(self, ignorefileextensions):
        self.ignorefileextensions = ignorefileextensions
        return self

    def setignoredirectories(self, ignoreirectories):
        self.ignoredirectories = ignoreirectories
        return self

    def setincludecomponentroots(self, includecomponentroots):
        self.includecomponentroots = self.isenabled(includecomponentroots)
        return self

    def setcommitmessageprefix(self, commitmessageprefix):
        self.commitmessageprefix = commitmessageprefix
        return self

    def setgitattributes(self, gitattributes):
        self.gitattributes = gitattributes
        return self

    @staticmethod
    def isenabled(stringwithbooleanexpression):
        return stringwithbooleanexpression == "True"

    def build(self):
        return ConfigObject(self.user, self.password, self.repourl, self.scmcommand, self.workspace,
                            self.useexistingworkspace, self.workdirectory, self.initialcomponentbaselines,
                            self.streamname, self.gitreponame, self.useprovidedhistory,
                            self.useautomaticconflictresolution, self.maxchangesetstoaccepttogether, self.clonedgitreponame, self.rootFolder,
                            self.previousstreamname, self.ignorefileextensions, self.ignoredirectories, self.includecomponentroots,
                            self.commitmessageprefix, self.gitattributes, 
                            self.component2load, self.svnrepodir)

class ConfigObject:
    def __init__(self, user, password, repourl, scmcommand, workspace, useexistingworkspace, workdirectory,
                 initialcomponentbaselines, streamname, gitreponame, useprovidedhistory,
                 useautomaticconflictresolution, maxchangesetstoaccepttogether, clonedgitreponame, rootfolder, previousstreamname,
                 ignorefileextensions, ignoredirectories, includecomponentroots, commitmessageprefix, gitattributes,
                 component2load, svnrepodir):
        self.user = user
        self.password = password
        self.repo = repourl
        self.scmcommand = scmcommand
        self.workspace = workspace
        self.useexistingworkspace = useexistingworkspace
        self.useprovidedhistory = useprovidedhistory
        self.useautomaticconflictresolution = useautomaticconflictresolution
        self.maxchangesetstoaccepttogether = maxchangesetstoaccepttogether
        self.workDirectory = workdirectory
        self.initialcomponentbaselines = initialcomponentbaselines
        self.streamname = streamname
        self.gitRepoName = gitreponame
        self.clonedGitRepoName = clonedgitreponame
        self.rootFolder = rootfolder
        self.logFolder = rootfolder + os.sep + "Logs"
        self.hasCreatedLogFolder = os.path.exists(self.logFolder)
        self.streamuuid = ""
        self.previousstreamname = previousstreamname
        self.previousstreamuuid = ""
        self.ignorefileextensions = ignorefileextensions
        self.ignoredirectories = ignoredirectories
        self.includecomponentroots = includecomponentroots
        self.commitmessageprefix = commitmessageprefix
        self.gitattributes = gitattributes
        self.component2load = component2load
        self.svnrepodir = svnrepodir

    def getlogpath(self, filename):
        if not self.hasCreatedLogFolder:
            os.makedirs(self.logFolder)
            self.hasCreatedLogFolder = True
        return self.logFolder + os.sep + filename

    def deletelogfolder(self):
        if self.hasCreatedLogFolder:
            shutil.rmtree(self.logFolder)
            self.hasCreatedLogFolder = False

    def gethistorypath(self, filename):
        historypath = self.rootFolder + os.sep + "History"
        return historypath + os.sep + filename

    def collectstreamuuid(self, streamname):
        if not streamname:
            return
        shouter.shout("Get UUID of configured stream " + streamname)
        showuuidcommand = "%s --show-alias n --show-uuid y show attributes -r %s -w %s" % (
            self.scmcommand, self.repo, streamname)
        output = shell.getoutput(showuuidcommand)
        splittedfirstline = output[0].split(" ")
        streamuuid = splittedfirstline[0].strip()[1:-1]
        return streamuuid

    def collectstreamuuids(self):
        self.streamuuid = self.collectstreamuuid(self.streamname)
        self.previousstreamuuid = self.collectstreamuuid(self.previousstreamname)


class ComponentBaseLineEntry:
    def __init__(self, component, baseline, componentname, baselinename):
        self.component = component
        self.baseline = baseline
        self.componentname = componentname
        self.baselinename = baselinename
