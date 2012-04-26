from django.shortcuts import render_to_response
from django.template import RequestContext
from chaqinterface.models import Conversation
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
import urllib, urllib2

# check out import code; code.interact(local=dict(globals().items() + locals().items()))

# Create your views here.
def index(request):
    conversation_log = None
    if (request.user.is_authenticated()):
        # get logs
        conversation_log = Conversation.objects.filter(user=request.user).order_by('-timestamp')[:5]

    return render_to_response('interface/index.html', {'conversation_log': conversation_log}, context_instance=RequestContext(request))

def about(request):
    return render_to_response(
        'interface/about.html', 
        {},
        context_instance = RequestContext(request)
    )

def logout(request):
    print 'should logout now'

def logs(request):
    if (request.user.is_authenticated()):
        # conversation_log = Conversation.objects.filter(user=request.user).order_by('-timestamp')[:5]
        conversation_log = Conversation.objects.filter(user=request.user).order_by('-timestamp')
        p = Paginator(conversation_log, 10)

        currentPage = 1
        if 'page' in request.GET:
            currentPage = int(request.GET['page'])
        if currentPage not in p.page_range:
            currentPage = 1

        conversation_log = p.page(currentPage).object_list

        return render_to_response(
            'interface/log.html',
            {
                'conversation_log': conversation_log,
                'pages': p.page_range,
                'currentPage': currentPage,
                'page': p.page(currentPage)
            },
            context_instance=RequestContext(request)
        )
    else:
        return render_to_response('interface/log.html', context_instance=RequestContext(request))

def ask(request):

    session_username = 'anonymous'
    if request.user.is_authenticated():
        user = User.objects.get(pk=request.user.id)
        session_username = user.username
        
    notice_message = ''
    # Check if a question exists
    if 'question' in request.POST:
        question = request.POST['question']
        status = 'OK'
    else:
        question = ''
        notice_message = 'You did not ask a question ...'
        status = 'ERROR'

    # Get answer from PyAIMLServer running on localhost:2465
    conn_string = "http://localhost:2465/ask/?u=" + urllib2.quote(session_username) + "&q=" + urllib2.quote(question)
    print conn_string
    conn = urllib2.urlopen(conn_string)
    answer = conn.read()

    conversation_log = None
    # insert question/answer into user's logs
    if request.user.is_authenticated():
        db_conversation = Conversation(
            user = user,
            question = question,
            answer = answer
        )
        db_conversation.save()
        # get logs
        conversation_log = Conversation.objects.filter(user=request.user).order_by('-timestamp')[:5]

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
            'conversation_log': conversation_log,
            'topic': 'N/A'
        }, 
        context_instance=RequestContext(request)
    )

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