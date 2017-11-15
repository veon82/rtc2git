import os
import configuration
import shouter
import shell
from gitFunctions import Commiter

class svnCommiter:

    @staticmethod
    def getcommitcommand(changeentry, comment):
        msg = (comment, "[RTC commit", changeentry.date, "by", changeentry.getgitauthor() + "]")
        return "svn commit -m %s" % (shell.quote(" ".join(msg)))

    @staticmethod
    def addandcommit(changeentry):
        config = configuration.get()
        if config.svnrepodir:
            shouter.shout("[SVN] current dir=%s svndir=%s" % (os.getcwd(), config.svnrepodir))
            # 1 - rsync current git dir to svn dir
            gitrepodir = os.getcwd()
            srcpath = os.path.join(gitrepodir, config.component2load)
            # if srcpath doesn't exist search for a different dir name
            if not os.path.exists(srcpath):
                for dirname in os.listdir(gitrepodir):
                    if dirname[0] != '.':
                        srcpath = os.path.join(gitrepodir, dirname)
            cmd = "rsync -r %s %s --delete" % (os.path.join(srcpath, "./"), os.path.join(config.svnrepodir, "trunk"))
            shouter.shout("[SVN] %s" % cmd)
            shell.execute(cmd)
            # 2 - chdir to svnrepo, add and commit
            os.chdir(config.svnrepodir)
            cmd = "svn add --force * --auto-props --parents --depth infinity -q"
            shouter.shout("[SVN] %s" % cmd)
            shell.execute(cmd)
            # 2.1 - mark deleted files for commit
            cmd = "svn status | grep '^!' | awk '{print $2}' | xargs svn delete"
            shouter.shout("[SVN] %s" % cmd)
            shell.execute(cmd)
            comment = Commiter.getcommentwithprefix(changeentry.comment)
            cmd = svnCommiter.getcommitcommand(changeentry, comment)
            shouter.shout("[SVN] %s" % cmd)
            shell.execute(cmd)
            shell.execute("svn update")
            # 3 - go back to current dir
            os.chdir(gitrepodir)
