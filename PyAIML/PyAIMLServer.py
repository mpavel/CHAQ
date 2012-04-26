#!/usr/bin/python
# -*- coding: UTF-8 -*-

import urllib2, os, marshal, re, nltk, aiml
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

k = None

class PyAIMLHandler(BaseHTTPRequestHandler):

    global k

    def do_GET(self):
        try:
            if self.path.startswith('/ask/'):
                querystring = self.path[5:]
                params = dict([part.split('=') for part in querystring.split('&')])
                print params
                session_username = params['?u'].encode('utf-8')
                question = urllib2.unquote(params['q'])
                question = self.normalizeQuestion(question)
                print question

                # load session data if it exists for username, 
                if not os.path.isfile("./session_data/" + session_username + ".ses"):
                    session_username = 'username'
                try:
                    sessionFile = file("./session_data/" + session_username + ".ses", "rb")
                    session = marshal.load(sessionFile)
                    sessionFile.close()
            
                    for pred,value in session.items():
                        k.setPredicate(pred, value, session_username)

                    debug_session_file(session, ['topic', 'it'])

                    # send the question to pyaiml and fetch the response
                    answer = k.respond(question, session_username)
                    answer = answer.replace("> <", "><")
                    answer = answer.replace("<br/><br/>", "<br/>")
                    answer = answer.replace("><br>", ">")
                    answer = answer.replace("><br/>", ">")

                    if len(answer) == 0:
                        answer = "I don't seem to have an answer for that. Maybe you can try rephrasing?"
                    print answer
                
                    # save session data to disk for username
                    session = k.getSessionData(session_username)
                    sessionFile = file("./session_data/" + session_username + ".ses", "wb")
                    marshal.dump(session, sessionFile)
                    sessionFile.close()

                    debug_session_file(session, ['topic', 'it'])

                    response = answer
                except:
                    answer = "Something went wrong and I could not answer that. Can you please try asking again?"

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(response)
                return

        except IOError:
            self.send_error(404, 'File Not Found %s' % self.path)

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("POST is not available on this server.")

    def normalizeQuestion(self, string):
        porter = nltk.PorterStemmer()
        tokens = nltk.word_tokenize(string)
        question = ' '.join([porter.stem(t) for t in tokens])
        question = question.upper()

        # pat = "[A-Z0-9\+-.\\\]\[\?#\*\!]+"
        pat = "[a-zA-Z0-9\.\+\(\)\# ]+"
        prog = re.compile(pat)
        result = prog.findall(question)
        if len(result) > 1:
            return ' '.join(result).encode('utf-8')
        else:
            return None

def main():
    
    global k
    # Bootstrap PyAIML
    k = aiml.Kernel()

    # Enabling Verbose mode, to help track down problems
    k.verbose(True)
    # Set the bot's name
    k.setBotPredicate("name","Chaq")

    brainLoaded = False
    forceReload = False
    while not brainLoaded:
        if forceReload:
            k.bootstrap(learnFiles="./std-startup.xml", commands="load stack overflow")
            brainLoaded = True
            k.saveBrain("./standard.brn")
        else:
            try:
                k.bootstrap(brainFile = "./standard.brn")
                brainLoaded = True
                print "Existing brain loaded"
            except:
                forceReload = True

    # debug_data = debug_session_file(session, ['topic', 'it'])

    try:
        server = HTTPServer(('', 2465), PyAIMLHandler)
        print 'Started PyAIML Server on port 2465 ...'
        server.serve_forever()
    except KeyboardInterrupt:
        print 'Shutting down PyAIML Server ...'

        # close kernel
        k.resetBrain()

        # shut down server
        server.socket.close()

def debug_session_file(data, params=[]):
    ret = {}
    if len(params) == 0:
        for pred,value in data.items():
            print str(pred) + ": " + str(value)
            ret[pred] = value
    else:
        for param in params:
            print param + ' : ' + data[param]
            ret[param] = data[param]
    return ret

if __name__ == '__main__':
    main()