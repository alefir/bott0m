import pydle
import subprocess
import sys
import exceptions
from bs4 import BeautifulSoup
import urllib
import ban
import admin
import tell
import chan
import wikipedia
import wolframalpha
import random
import urllib.request
import urllib.parse
import re
import pyjokes

# Set our name and version.
name = "Python3Bot"
version = "0.2-wiki"
cmd = "`"

def error(error, fatal = False):
    """ Prints error to stdout, flushing the output, and exiting if it's a fatal error. """
    if not fatal:
        print("ERROR: {}".format(error), flush = True)
    else:
        print("FATAL ERROR: {}".format(error), flush = True)
        sys.exit(1)

def warning(warning):
    """ Prints warning to stdout, flushing the output. """
    print("WARNING: {}".format(warning), flush = True)

def debug(debug):
    """ Prints debug to stdout, flushing the output. """
    print("DEBUG: {}".format(debug), flush = True)

def is_yes(s):
    """ Returns whether the string means True or False """
    s = s.lower()
    if s == "true" or s == "yes" or s == "y":
        return True
    else:
        return False

class Bot(pydle.Client):
    """ The main bot class. Handles events, and the raw IRC connection. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_links = {}

    def quit(self, message=None):
        """ Quits network. """
        debug("Quitting. Reason: {}".format(message))
        self.Bans.save_bans()
        self.Admins.save_admins()
        self.Tells.save_tells()
        self.Channels.save_chans()
        return super().quit(message)

    def on_connect(self):
        super().on_connect()
        self.rawmsg("MODE", self.config.nick, self.config.usermode)
        self.Bans = ban.BanManager("bans.dat", self)
        self.Admins = admin.AdminManager("admins.dat", self)
        self.Tells = tell.TellManager("tells.dat", self)
        self.Channels = chan.ChannelManager("channels.dat", self)

    def is_admin(self, target, account):
        for each in self.Admins.admins:
            if target == each.target and account == each.nick:
                return True
        if account == self.config.owner:
            return True
        return False

    @pydle.coroutine
    def __handle_internal(self, target, source, message):
        message = message.strip(' ')

        if source == 'lurk':
            return

        # Test for Links
        links = re.findall('(http[s]?:\/\/[^\s]*)', message)
        for link in links:
            title = self.cached_links.get(link, '')
            if title == '':
                url = urllib.request.urlopen(link)
                page = BeautiffulSoup(url)
                title = page.title.string
                self.cached_links[link] = title
            self.__respond(target, source, "[ {} ]".format(title))

        if message == cmd+"version":
            self.notice(target, "{}: {}, Version: {}. {}".format(source, name, version, target))

        if message == cmd+"quit":
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                self.quit("Recieved a quit command.")
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

        if message.startswith(cmd+"remove"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit=2)
                pmsg = ""
                if len(args) == 2:
                    pmsg = "Removed by {}".format(source)
                elif len(args) == 3 and args[2] != "":
                    pmsg = "Removed by {} (".format(source) + args[2] + ")"
                else:
                    self.notice(target, "{}: Invalid command invocation.".format(source))
                    return
                if args[1] == self.config.nick:
                    self.notice(target, "{}: I refuse to remove myself.".format(source))
                    return

                self.rawmsg("REMOVE", target, args[1], pmsg)
                self.notice(target, "{}: Removed {}.".format(source, args[1]))
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

        if message.startswith(cmd+"ban"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit=3)
                remove = False
                reason = ""
                if len(args) == 2:
                    ban_number = self.Bans.add_ban(target, args[1])
                    self.__respond(target, source, "{}: Bad added on {} (Channel: {}) as ban number {}.".format(source, args[1], target, ban_number))
                elif len(args) > 2:
                    if len(args) == 3:
                        reason = "Banned by {}".format(source)
                    elif len(args) == 4:
                        reason = "Banned by {} ({})".format(source, args[3])
                    else:
                        self.__respond(target, source, "{}: Invalid command invocation.".format(source))
                        return

                    ban_number = self.Bans.add_ban(target, args[1])
                    self.rawmsg("REMOVE", target, args[2], reason)
                    self.__respond(target, source, "{}: Ban added on {} (Channel: {}) as ban number {}.".format(source, args[1], target, ban_number))
                else:
                    self.__respond(target, source, "{}: Invalid command invocation.".format(source))
                    return
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

        if message.startswith(cmd+"rmban"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', masxplit = 1)
                if len(args) == 2:
                    try:
                        num = int(float(args[1]))
                    except ValueError:
                        self.__respond(target, source, "{}: Invalid number.".format(source))
                        return
                    status = self.Bans.remove_ban(num)
                    if status != 0:
                        self.__respond(target, source, "{}: Ban number out of range.".format(source))
                    else:
                        self.__respond(target, source, "{}: Ban lifted.".format(source))
                else:
                    self.__respond(target, source, "{}: Invalid command invocation.".format(source))
                    return
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

        if message == cmd+"lsban":
            self.__notice(source, "Bot ban list:")
            for i in range(0, len(self.Bans.bans)):
                self.notice(source, "{}. Channel: {} | Hostmask: {}".format(i, self.Bans.bans[i].target, self.Bans.bans[1].mask))
            self.notice(source, "End of bot ban list.")

        if message.startswith(cmd+"quiet"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 2)
                if len(args) ==2:
                    self.rawmsg("MODE", target, '+q', args[1])
                else:
                    return
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

        if message.startswith(cmd+"unquiet"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("MODE", target, '-q', args[1])
                else:
                    self.__respond(target, source, "{}: Invalid command invocation".format(source))
                    return
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command".format(source))

        if message.startswith(cmd+"yt"):
            args = message.split(' ', maxsplit = 1)
            if len(args) == 2:
                query_string = urllib.parse.urlencode({"search_query" : args[1]})
                html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
                search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
                yturl = "http://www.youtube.com/watch?v={}".format(search_results[0])
                ytpage = BeautifulSoup(urllib.request.urlopen(yturl))
                self.__respond(target, source, "[YT] {} | {}".format(ytpage.title.string, yturl))
            else:
                self.__respond(target, source, "[YT] Sorry, you need to tell me what you want")

        if message.startswith(cmd+"say"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 2)
                if len(args) == 3:
                    self.__respond(args[1], args[1], args[2])
                else:
                    self.__respond(target, source, "[SAY] You did the command wrong")

        if message.startswith(cmd+"wiki"):
            args = message.split(' ', maxsplit = 1)
            if len(args) == 2:
                if args[1] == "random":
                    try:
                        self.__respond(target, source, "[Wiki] {}".format(wikipedia.summary(wikipedia.random(pages=1), sentences=2)))
                    except Exception as e:
                        print(str(e))
                else:
                    try:
                        self.__respond(target, source, "[Wiki] {} | {}".format(wikipedia.summary(args[1], sentences=3), wikipedia.page(args[1]).url))
                    except wikipedia.exceptions.DisambiguationError as e:
                        output = str(e)
                        print(output)
                        split = output.split('\n')
                        self.__respond(target, source, "[Wiki] {}\n{}\n{}\n{}\n{}".format(split[0], split[1], split[2], split[3], split[4]))
                    except wikipedia.exceptions.PageError as e:
                        self.__respond(target, source, "[Wiki] \"{}\" does not match any pages".format(args[1]))
            else:
                self.__respond(target, source, "[Wiki] Sorry, you need to tell me what you want")

        if message.startswith(cmd+"wolf"):
            args = message.split(' ', maxsplit = 1)
            app_id = "3HLT6T-EG7UJL8574"
            if args[1] == 'Who is God?':
                self.__respond(target, source, "[W|A] That would be alefir")
            elif len(args) == 2:
                try:
                    client = wolframalpha.Client(app_id)
                    res = client.query(args[1])
                    self.__respond(target, source, "[W|A] {}: {}".format(args[1], next(res.results).text))
                except BaseException as e:
                    print(str(e))
                    self.__respond(target, source, "[W|A] Sorry, I didn't understand that")
            else:
                self.__respond(target, source, "[W|A] Sorry, you need to tell me what you want")

        if message == cmd+"joke":
            self.__respond(target, source, '[Joke] {}'.format(pyjokes.get_joke()))

        if message == cmd+"fortune":
            def random_line(fname):
                lines = open(fname).read().splitlines()
                return random.choice(lines)
            self.__respond(target, source, "[Fortune] {}".format(random_line('proverbs.txt')))

        if message.startswith(cmd+"op"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("MODE", target, '+o', args[1])
                else:
                    self.rawmsg("MODE", target, '+o', source)
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command".format(source))

        if message.startswith(cmd+"deop"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', macsplit = 1)
                if len(args) == 2:
                    if args[1] == self.config.nick:
                        self.__respond(target, source, "{}: I refuse to deop myself.".format(source))
                        return
                    self.rawmsg("MODE", target, '-o', args[1])
                else:
                    self.rawmsg("MODE", target, '-o', source)
            else:
                self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

        if message.startswith(cmd+"voice"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("MODE", target, '+v', args[1])
                else:
                    self.rawmsg("MODE", target, '+v', source)
                    return
            else:
                self.__respond(target, source, "{}: You need admin prics to execute that command.".format(source))

        if message.startswith(cmd+"devoice"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("MODE", target, '-v', args[1])
                else:
                    self.rawmsg("MODE", target, '-v', source)
                    return
            else:
                self.__respond(target, source, "{}: You need admin prics to execute that command.".format(source))

        if message.startswith(cmd+"exempt"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("MODE", target, '+e', args[1])
                else:
                    self.rawmsg("MODE", target, '+e', "*!*@", host['hostname'])
                    return
            else:
                self.__respond(target, source, "{}: You need admin prics to execute that command.".format(source))

        if message.startswith(cmd+"unexempt"):
            host = yield self.whois(source)
            if self.is_admin(target, host['account']):
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("MODE", target, '-e', args[1])
                else:
                    self.rawmsg("MODE", target, '-e', "*!*@", host['hostname'])
                    return
            else:
                self.__respond(target, source, "{}: You need admin prics to execute that command.".format(source))

        if message.startswith(cmd+"admin"):
            host = yield self.whois(source)
            if host['account'] == self.config.owner:
                args = message.split(' ', maxsplit = 1)
                adminnum = self.Admins.add_admin(target, args[1])
                self.__respond(target, source, "{}: Admin \"{}\" added on channel {} as number {}.".format(source, args[1], target, adminnum))
            else:
                self.__respond(target, source, "{}: You need to the the bot owner to run that command.".format(source))

        if message.startswith(cmd+"rmadmin"):
            host = yield self.whois(source)
            if host['account'] == self.config.owner:
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    try:
                        num = int(float(args[1]))
                    except ValueError:
                        self.__respond(target, source, "{}: Invalid number.".format(source))
                        return
                    retval = self.Admins.remove_admin(num)
                    if retval == 0:
                        self.__respond(target, source, "{}: Admin removed.".format(source))
                    else:
                        self.__respond(target, source, "{}: Admin number out of range.".format(source))
                else:
                    self.__respond(target, source, "{}: Invalid command invocation".format(source))
            else:
                self.__respond(target, source, "{}: You need to be the bot owner to run that command.".format(source))

        if message == cmd+"lsadmin":
            self.notice(source, "Bot admin list:")
            for i in range(0, len(self.Admins.admins)):
                self.notice(source, "{}. Channel: {} | Account: {}".format(i, self.Admins.admins[i].target, self.Admins.admins[1].nick))
            self.notice(source, "End of bot admin list.")

        if message.startswith(cmd+"tell"):
            args = message.split(' ', maxsplit = 2)
            if len(args) == 3:
                tell_num = self.Tells.add_tell(target, args[1], source, args[2])
                self.__respond(target, source, "{}: I'll pass that on when {} is around. The tell ID is {}.".format(source, args[1], tell_num))
            else:
                self.__respond(target, source, "{}: Invalid command invocation.".format(source))
            return

        if message == cmd+"lstell":
            self.notice(source, "Bot tell list:")
            for i in range(0, len(self.Tells.tells)):
                if self.Tells.tells[i].harbinger == source:
                    self.notice(source, "{}. Channel: {} | To: {} | From: {} | Message: {}".format(i, self.Tells.tells[i].target, self.Tells.tells[i].nick, self.Tells.tells[i].harbinger, self.Tells.tells[i].message))
                else:
                    self.notice(source, "{}. Channel: {} | To: {} | From: {}".format(i, self.Tells.tells[i].target, self.Tells.tells[i].nick, self.Tells.tells[i].harbinger))
            self.notice(source, "End of bot tell list.")

        if message.startswith(cmd+"rmtell"):
            args = message.split(' ', maxsplit = 1)
            if len(args) == 2:
                try:
                    num = int(float(args[1]))
                except BaseException as e:
                    self.__respond(target, source, "{}: Invalid number.".format(source))
                    return
                if num > len(self.Tells.tells)-1:
                    self.__respond(target, source, "{}: Number out of range.".format(source))
                    return
                else:
                    tell = self.Tells.tells[num]
                    if source == tell.harbinger:
                        self.Tells.remove_tell(num, activate = False)
                        self.__respond(target, source, "{}: Tell removed.".format(source))
                        return
                    else:
                        host = yield self.whois(source)
                        if self.is_admin(target, host['account']):
                            self.Tells.remove_tell(num, activate = False)
                            self.__respond(target, source, "{}: Tell forcibly removed.".format(source))
                            return
                        else:
                            self.__respond(target, source, "{}: You are not authorized to remove someone else's tell.".format(source))
                            return
            else:
                self.__respond(target, source, "{}: Invalid command invocation.".format(source))

        if message.startswith(cmd+"join"):
            host = yield self.whois(source)
            if self.config.owner == host['account']:
                args = message.split(' ')
                if len(args) == 2:
                    self.Channels.join_chan(args[1])
                    self.__respond(target, source, "{}: Channel joined.".format(source))
                else:
                    self.__respond(target, source, "{}: Invalid command invocation.".format(source))
            else:
                self.__respond(target, source, "{}: You need to be the bot owner to execute this command.".format(source))

        if message.startswith(cmd+"part"):
            host = yield self.whois(source)
            args = message.split(' ')
            if len(args) == 2:
                try:
                    num = int(float(args[1]))
                except ValueError:
                    self.__respond(target, source, "{}: Invalid Number.".format(source))
                    return
                if num > len(self.Channels.channels)-1:
                    self.__respond(target, source, "{}: Number out of range.".format(source))
                    return
                try:
                    if self.is_admin(self.Channels.channels[num].name, host['account']):
                        self.Channels.part_chan(num, source)
                        self.__respond(target, source, "{}: Channel removed.".format(source))
                except BaseException as e:
                    print(str(e), type(e))
            else:
                self.__respond(target, source, "{}: Invalid command invocation.".format(source))

        if message == cmd+"lschans":
            self.notice(source, "Bot channel list:")
            i = 0
            for each in self.Channels.channels:
                self.notice(source, "{}. {}".format(i, each.name))
                i += 1
            self.notice(source, "End of bot channel list.")

        if message == cmd+"git":
            args = message.split(' ')
            if len(args) == 2:
                self.__respond(target, source, "https://github.com/{}".format(args[1]))
            else:
                self.__respond(target, source, "Take a look in my panties at https://github.com/alefir/bott0m")

        if message == cmd+"ghost":
            host = yield self.whois(source)
            if host['account'] == self.config.owner:
                self.message("NickServ", "GHOST {} {}".format(self.config.nick, self.config.sasl_password))
                self.respond(target, source, "{}: Ghosted.".format(source))
            else:
                self.__respond(target, source, "{}: You must be the bot owner to execute that command.".format(source))

        if message.startswith(cmd+"nick"):
            host = yield self.whois(source)
            if self.config.owner == host['account']:
                args = message.split(' ', maxsplit = 1)
                if len(args) == 2:
                    self.rawmsg("NICK", args[1])
                else:
                    self.rawmsg("NICK", self.config.nick)

        if message == cmd+"help":
            helptext = "" \
            "Command List:\n" \
            " <name>    | <arguments>                   | <description>\n" \
            "`version   |                               | Displays the version information of the bot\n" \
            "`help      |                               | Shows this help\n" \
            "`quit      |                               | Kills the bot\n" \
            "`remove    | <nick> [reason]               | Removes <nick> from channel with optional [reason]\n" \
            "`ban       | <mask> [ <nick> [reason] ]    | Bans the mask <mask> and can remove <nick> with [reason] if specified\n" \
            "`rmban     | <number>                      | Lifts ban specified by <number>\n" \
            "`lsban     |                               | Lists the banlist\n" \
            "`unban     | <mask>                        | Unbans the specified <mask>\n" \
            "`quiet     | <mask>                        | Sets quiet on <mask>\n" \
            "`unquiet   | <mask>                        | Removes quiet on <mask>\n" \
            "`op        | [nick]                        | Ops [nick] if specified, otherwise you\n" \
            "`deop      | [nick]                        | Deops [nick] if specified, otherwise you\n" \
            "`voice     | [nick]                        | Voices [nick] if specified, otherwise you\n" \
            "`devoice   | [nick]                        | Devoices [nick] if specified, otherwise you\n" \
            "`exempt    | [hostmask]                    | Sets ban exempt on [hostmask] if specified, otherwise you\n" \
            "`unexempt  | [hostmask]                    | Removes ban exempt on [hostmask] if specified, otherwise you\n" \
            "`admin     | <account>                     | Adds <account> as admin in this channel\n" \
            "`rmadmin   | <number>                      | Removes admin specified by <number>\n" \
            "`lsadmin   |                               | Lists all admins\n" \
            "`tell      | <nick> <message>              | Tells me to pass <message> onto <nick> next time they type a message\n" \
            "`rmtell    | <number>                      | Removes a tell by <number>. You can only remove you own tells (except admins)\n" \
            "`lstell    |                               | Lists all tells. Message only displayed on your own tells\n" \
            "`ghost     |                               | Disconnect bot ghost\n" \
            "`nick      | [nick]                        | Changes bot nick to [nick] if specified, otherwise to defualt\n" \
            "           |                               |\n" \
            "`wiki      | <query | random>              | Searches wikipedia for <query> or shows a <random> page\n" \
            "`yt        | <query>                       | Searches YouTube for <query>\n" \
            "`wolf      | <query>                       | Queries Wolfram|Alpha for <query>\n" \
            "`fortune   |                               | Tells a fortune\n" \
            "`joke      |                               | Tells a joke\n" \
            "End of help"

            self.notice(source, helptext)

        if len(self.Tells.tells) > 0:
            for i in range(len(self.Tells.tells)):
                if self.Tells.tells[i].nick == source:
                    self.Tells.remove_tell(i)
    def __respond(self, target, source, message):
        if self.is_channel(target):
            self.message(target, message)
        else:
            self.message(source, message)

    def on_message(self, target, source, message):
        super().on_message(target, source, message)
        self.__handle_internal(target, source, message)
        for each in self.plugin.plugin_commands:
            value = each.split(":")
            if message.startswith("!{}".format(value[0])):
                module_obj = self.plugin.plugins[value[2]]
                function_obj = getattr(module_obj, value[1])
                warning("Plugin returned: {}".format(function_onj()))
        debug("Target: {}, Source: {}, Message: {}".format(target, source, message))

    def on_kick(self, channel, target, by, reason = None):
        super().on_kick(channel, target, by, reason)
        if target == self.config.nick:
            self.join(channel)

    def on_part(self, channel, user, message = None):
        super().on_kick(channel, user, message)
        on_list = False
        for each in self.Channels.channels:
            if each.name == channel:
                on_list = True
        if user == self.config.nick and on_list:
            self.join(channel)

    def on_raw(self, data):
        super().on_raw(data)
        data = str(data)
        data = data.strip("\n")
        if data.find("PING") == -1 and data.find("PRIVMSG") == -1:
            debug(data)

    def on_join(self, channel, user):
        super().on_join(channel, user)
        account = self.whois(user)
        if self.config.deop_owner and account['account'] == self.config.owner:
            self.rawmsg("MODE", channel, '-o', nick)

    def on_unknown(self, message):
        warning("Recieved an unknown command: {}".format(message))

    def on_data_error(self, exception):
        error("Caught a socket exception. {} {}".format(type(exception), str(exception)), fatal = True)
