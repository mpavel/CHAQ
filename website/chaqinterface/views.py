from django.shortcuts import render_to_response
from django.template import RequestContext
from chaqinterface.models import Conversation
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
import marshal
import os.path

# check out import code; code.interact(local=dict(globals().items() + locals().items()))

from PyAIML import aiml

# Create your views here.
def index(request):
    return HttpResponseRedirect("/")
    return render_to_response('interface/index.html', {}, context_instance=RequestContext(request))

def about(request):
    return render_to_response(
        'interface/about.html', 
        {},
        context_instance = RequestContext(request)
    )

def logout(request):
    print 'should logout now'

def logs(request):
    conversation_log = Conversation.objects.all().order_by('-timestamp')[:5]
  
    return render_to_response(
        'interface/log.html',
        {
            'conversation_log': conversation_log,
        }
    )

def ask(request):

    session_username = 'anonymous'
    if request.user.is_authenticated():
        user = User.objects.get(pk=request.user.id)
        session_username = user.username
        print vars(request.user) #.id

    # print "request.session:"
    # for key,val in request.session.items():
    #   print str(key) + " ---> " + str(val)
    notice_message = ''

    # Check if a question exists
    if 'question' in request.POST:
        question = request.POST['question']
        status = 'OK'
    else:
        question = ''
        notice_message = 'You did not ask a question ...'
        status = 'ERROR'

    # load pyaiml kernel
    k = aiml.Kernel()

    # load session data if it exists for username
    if os.path.isfile("session_data/" + session_username + ".ses"):
        sessionFile = file("session_data/" + session_username + ".ses", "rb")
        session = marshal.load(sessionFile)
        sessionFile.close()
    
        for pred,value in session.items():
            k.setPredicate(pred, value, session_username)


    # Enabling Verbose mode, to help track down problems
    k.verbose(True)
    # Set the bot's name
    k.setBotPredicate("name","Chaq")

    brainLoaded = False
    forceReload = False
    while not brainLoaded:
        if forceReload:
            k.bootstrap(learnFiles="PyAIML/std-startup.xml", commands="load aiml b")
            brainLoaded = True
            k.saveBrain("PyAIML/standard.brn")
        else:
            try:
                k.bootstrap(brainFile = "PyAIML/standard.brn")
                brainLoaded = True
                print "Existing brain loaded"
            except:
                forceReload = True
  
    # send the question to pyaiml and fetch the response
    answer = k.respond(question, session_username)

    # save session data to disk for username
    # this should be done every so often, or at logout, etc
    session = k.getSessionData(session_username)
    sessionFile = file("session_data/" + session_username + ".ses", "wb")
    marshal.dump(session, sessionFile)
    sessionFile.close()

    # close kernel

    print "Session file written to disk\n"

    k.resetBrain()

    debug_session_file(session)
    print "\n\n"

    # insert question/answer into user's logs
    # conversation = new Conversation
    # conversation.question = request.POST['question']
    # conversation.answer   = response

    conversation = {
        'status'  : status,
        'question': question,
        'answer'  : answer
    }

    # return to main page and send response back
    return render_to_response(
        'interface/index.html', 
        {
            'status'        : 'OK',
            'notice_message': notice_message, 
            'conversation'  : conversation,
        }, 
        context_instance=RequestContext(request)
    )

def debug_session_file(data):
    for pred,value in data.items():
        print str(pred) + ": " + str(value)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            return HttpResponseRedirect("/")
    else:
        form = UserCreationForm()
 
    return render_to_response(
        "register.html", 
        {'form': form,  },
        context_instance = RequestContext(request)
    )