#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Small script that fetches all text from the database (Q&A) and saves it
as AIML files so it can be used with PyAIML.
"""

import os, sys, MySQLdb, nltk, marshal, optparse, re
from BeautifulSoup import BeautifulSoup
from xml.dom.minidom import Document, parseString

def strip(html):
    s = ""

    if html is not None:
        tags_to_keep = ['code', 'pre']
        soup = BeautifulSoup(html)
        allSoup = soup.findAll(True)
        if len(allSoup) == 0:
            s += unicode(''.join(soup.findAll(text=True)))
        else:
            for tag in allSoup:
                # Remove all tags but [tags_to_keep]
                if tag.name in tags_to_keep:
                    s += unicode(tag)
                else:
                    s += unicode(''.join(tag.findAll(text=True)))
    return s
    # return ''.join(BeautifulSoup(html).findAll(text=is_not_code))

def saveFile(data, filename):
    f = open(filename, "a+")
    f.write(data)
    f.close()

def log(string):
    string = str(string) + "\n"
    print string

# list of tags used to crawl Stack Overflow, from SOcrawler
tag_list = set(['c#', 'java', 'php', 'javascript', 'jquery', 'android', 'iphone', 'c++', 'asp.net', '.net', 'python', 'mysql', 'html', 'sql', 'ruby-on-rails', 'css', 'ajax', 'linux', 'django', 'json', 'perl', 'git', 'wordpress', 'c'])
# dictionary containing the root elements for the AIML files, grouped in tags
docs = {}

# Database connection
try:
    _db = MySQLdb.connect(host = 'localhost',
                          user = 'crawler',
                          passwd = 'crawlpass12',
                          db = 'socrawler')
except MySQLdb.Error, e:
    log("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

def normalizeQuestion(qin, stem=True):
    """
    A way to improve this would be to look through the 
    tokens and see if any of them are not words or letters 
    (example: - , * , ( , ) , etc).
    In these cases, leave the original intact and make a copy 
    that removes them and just leaves the text inside. Maybe 
    this can be done with a regex test??? or a length test???
    """
    if stem:
        porter = nltk.PorterStemmer()
        tokens = nltk.word_tokenize(qin)
        question = ' '.join([porter.stem(t) for t in tokens])
    else:
        question = qin

    question = question.upper()

    # pat = "[A-Z0-9\+-.\\\]\[\?#\*\!]+"
    pat = "[a-zA-Z0-9\.\+\(\)\# ]+"
    prog = re.compile(pat)
    result = prog.findall(question)
    # tokens = nltk.word_tokenize(question)
    # if len(tokens) > 1:
    #     for token in tokens:
    #         token = ''.join(ch for ch in token if ch.isalnum()).upper()
    #         qout += token + ' '
    if len(result) > 1:
        return ' '.join(result)
    else:
        return None

def getQuestions():
    global tag_list
    global _db
    c = _db.cursor()

    try:
        c.execute("""
        SELECT 
            question.id AS questionID,
            question.title AS question,
            question.body AS questionBody,
            question.tags AS tags,
            answer.id AS answerID,
            answer.body AS answer
        FROM question
        LEFT JOIN answer 
        ON question.id = answer.qid 
        ORDER BY question.id ASC
        LIMIT 0,2000
        """)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))
    
    while (1):
        row = c.fetchone()
        if row == None:
            break

        item = {
            'questionID': row[0], 
            'question': row[1].decode("utf-8"), 
            'questionBody': strip(row[2]), 
            'tags': row[3],
            'answerID': row[4], 
            'answer': row[5].decode("utf-8")
        }

        item['question'] = normalizeQuestion(item['question'])

        if item['question'] is not None:
            tags = set(eval(item['tags'].encode('utf-8')))
            # intersect the row's tags with the tags from crawler, to only get the common used ones
            tags_to_use = tag_list & tags
            if len(tags_to_use) == 0:
                tags_to_use = ['unknown']

            for tag in tags_to_use:
                # And append that data in multiple files according to the tags associated
                addAiml(item, tag)

def writeStemmedQuestions():
    global _db
    c = _db.cursor()
    i = _db.cursor()

    # truncate table first (needs permissions added to the user)
    # try:
    #     c.execute("""TRUNCATE TABLE stemmed_question""")
    # except MySQLdb.Error, e:
    #     log("Error %d: %s" % (e.args[0], e.args[1]))

    try:
        c.execute("""
        SELECT 
            question.id AS questionID,
            question.title AS question, 
            question.tags AS tags 
        FROM question
        ORDER BY question.id ASC
        # LIMIT 0,100
        """)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))
    
    while (1):
        row = c.fetchone()
        if row == None:
            break

        question = normalizeQuestion(row[1])
        if question is not None:
            print str(row[0]) + ': ' + question
            try:
                i.execute("""
                INSERT INTO stemmed_question (id, stemmed_question, tags)
                VALUES (%s, %s, %s)
                """, (row[0], question, row[2]))
            except MySQLdb.Error, e:
                log("Error %d: %s" % (e.args[0], e.args[1]))

    i.close()
    # Execute all insert statements
    _db.commit()

def saveQuestionStarts(limit=50):
    """
        This function builds a set of words to be used in AIML's srai tags (Symbolic Reduction).
        It does this by going through all the stemmed questions in the database and selecting their
        first 7 - 2 words, grouping by them.
        This results in a list similar to the following (for 3 words):
        
        cnt     first_words
        ----    -----------
        9003    how do i
        8441    how can i
        3703    what is the
        2976    is there a
        2686    how to get

        Where cnt is the number of questions that start with "how do i".

        The results are saved in a set, in the following way:
        For the string "how do i", 3 attempts to insert into the set will be made:
            1. full string "how do i"
            2. remove last words and add: "how do"
            3. remove last word and add: "how"
            4. no other word to add
        The set will end up with unique references from these words, from 1 to 7 words long.
        These will be written in AIML files similar to the following:
        <category>
            <pattern>HOW DO I *</pattern>
            <template>
                <srai><star/></srai>
            </template>
        </category>

        <category>
            <pattern>HOW DO *</pattern>
            <template>
                <srai><star/></srai>
            </template>
        </category>

        <category>
            <pattern>HOW *</pattern>
            <template>
                <srai><star/></srai>
            </template>
        </category>

        By doing this we make sure we can ask the same question in many different ways.
        IMPORTANT!
        The rest of the question (<star/>) will be created by going through all the stemmed
        questions again and removing the beginning part of the question by checking through
        all entries in the set.
    """
    global _db
    c = _db.cursor()

    min_count = 1
    max_count = 7
    count = min_count
    questions = set([])

    while (count <= max_count):
        # Fetch top 'count' words in stemmed questions
        try:
            c.execute("""
                SELECT count( id ) AS cnt, SUBSTRING_INDEX( UPPER( stemmed_question ) , ' ', %s ) AS first_words
                FROM stemmed_question
                GROUP BY first_words
                HAVING cnt > %s
                ORDER BY cnt DESC
            """, (count, limit))
        except MySQLdb.Error, e:
            log("Error %d: %s" % (e.args[0], e.args[1]))

        while (1):
            row = c.fetchone()
            if row == None:
                break

            questions.add(row[1])
            print row[1]
        count += 1

    # remove old files
    try:
        os.remove(sys.path[0] + '/question_starts.sess')
    except OSError, e:
        print e
    try:
        os.remove(sys.path[0] + '/aiml/so-srai.aiml')
    except OSError, e:
        print e
    # save questions starts in file (marshal dump)
    questions = list(questions)
    filename = sys.path[0] + '/question_starts.sess'
    qs = file(filename, "wb")
    marshal.dump(questions, qs)
    qs.close()

    # Generate srai AIML file
    saveAimlQuestionStart(questions)

def saveAimlQuestionStart(questions):
    doc = Document()
    # create the root tag
    aiml = doc.createElement("aiml")
    aiml.setAttribute("version", "1.0")
    doc.appendChild(aiml)

    meta = doc.createElement("meta")
    meta.setAttribute("name", "author")
    meta.setAttribute("content", "SimpleAIMLGenerator")
    aiml.appendChild(meta)
    meta = doc.createElement("meta")
    meta.setAttribute("name", "language")
    meta.setAttribute("content", "en")
    aiml.appendChild(meta)

    # Create change topic rule
    change_topic_rule = "<category><pattern>CAN WE TALK ABOUT *</pattern><template><random><li>Of course, let's talk about <star/>!</li><li>Sure, we can talk about <star/>!</li><li>Fire on, let's talk about <star/>.</li><li>We can talk about <star/> as long as you want!</li></random><think><set name=\"it\"><set name=\"topic\"><star/></set></set></think></template></category>"
    ctr = parseString(change_topic_rule)
    aiml.appendChild(ctr.childNodes[0])

    for q in questions:
        # initialize the elements required in AIML
        category = doc.createElement("category")
        pattern = doc.createElement("pattern")
        template = doc.createElement("template")
        srai = doc.createElement("srai")
        star = doc.createElement("star")
        pattern_text = q + ' *'
        pattern.appendChild(doc.createTextNode(pattern_text))
        category.appendChild(pattern)
        srai.appendChild(star)
        template.appendChild(srai)
        category.appendChild(template)
        aiml.appendChild(category)

    # save aiml to file
    filename = sys.path[0] + '/aiml/so-srai.aiml'
    f = open(filename, 'a+')
    f.write(doc.toprettyxml("  "))
    f.close()

def addAiml(item, tag):
    """
    Very important when generating the AIML files based on the
    questions in the database, is to REMOVE the first few words
    from questions, after they are normalized.
    Once normalized, the questions_starts.sess should be loaded
    and looped through each item. Test if the first few words of
    any element is the same with the same number of first words 
    in the question we want to write in AIML.

    This is very important for the so-srai.aiml tags.

    Example:
    We have multiple patterns in so-srai.aiml:
    <pattern>
      HOW TO DETECT *
    </pattern>
    <pattern>
      HOW TO *
    </pattern>

    What this means is that when we ask the question:
    "How to detect fonts in javascript?"
    the first pattern is matched, thus returning an empty 
    response, even if we do have a valid response for the 
    question.
    This happens because the pattern then used (the *) 
    remains only "fonts in javascript", instead of 
    "detect fonts in javascript" for which we have a response.

    Another problem occurs when we haven't stripped enough from 
    what we thought was the roog question.

    So if we have another pattern: fonts in *, then the 
    question won't be answered, because this will happen:
     1. look for: how to detect fonts in javascript
     2. find: how to detect *
     3. strip to and look for: fonts in javascript
     4. find: fonts in *
     5. strip and look for: javascript

    This means if we have no "javascript" pattern, nothing will
    return even if we have the answer to the full question.
    For this we need to run through ALL question_starts and 
    improve the algorithm to remove words from the QUESTION 
    as long as we find the first word(s) in QUESTION equal to
    a question_start.
    """
    # AIML documents
    global docs

    # Get the data for each Q&A
    question = split_start(item['question'])
    question = question.encode('utf-8')
    answer = item['answer']
    answer = answer.replace("\n", "<br/>")
    answer = answer.encode('utf-8')
    doc = docs[tag]
    aiml = doc.childNodes[0]

    # initialize the elements required in AIML
    category = doc.createElement("category")
    pattern = doc.createElement("pattern")
    template = doc.createElement("template")
    pattern.appendChild(doc.createTextNode(question))
    category.appendChild(pattern)
    template.appendChild(doc.createCDATASection(answer))
    category.appendChild(template)
    aiml.appendChild(category)

    docs[tag] = doc

def split_start(question):
    # Load file with questions starts
    filename = "question_starts.sess"
    if os.path.isfile(filename):
        sessFile = file(filename, "rb")
        starts = marshal.load(sessFile)
        sessFile.close()

    # sort all questions in a list, from longer to shorter
    starts.sort(lambda x,y: cmp(len(y), len(x)))

    for start in starts:
        l = len(start)
        if start[:l] == question[:l]:
            if question[l] == ' ':
                return question[l+1:]
            else:
                return question[l:]
    return question
# HOW TO GRAB THE CONTENT OF HTML TAG
def main():

    global tag_list, docs

    p = optparse.OptionParser(description="Simple AIML Generator",
        prog="SimpleAIMLGenerator",
        version="v0.1",
        usage="%prog -a generate-aiml / stem-questions / generate-srai")
    p.add_option('-a', '--action', dest='action', default='help')
    (options, arguments) = p.parse_args()

    if options.action:
        action = options.action
    else:
        action = 'help'
    
    if action == 'stem-questions':
        print 'Generating stemmed questions.'
        writeStemmedQuestions()
    elif action == 'generate-aiml':
        print 'Generating AIML files in "aiml/so-<tag>.aiml"'
        for tag in tag_list:
            doc = Document()
            # create the root tag
            aiml = doc.createElement("aiml")
            aiml.setAttribute("version", "1.0")
            doc.appendChild(aiml)

            meta = doc.createElement("meta")
            meta.setAttribute("name", "author")
            meta.setAttribute("content", "SimpleAIMLGenerator")
            aiml.appendChild(meta)
            meta = doc.createElement("meta")
            meta.setAttribute("name", "language")
            meta.setAttribute("content", "en")
            aiml.appendChild(meta)


            # topic = doc.createElement("topic")
            # topic.setAttribute("name", tag.upper())
            # aiml.appendChild(topic)

            docs[tag] = doc
            # TODO: Add topic for each tag

        getQuestions()

        for tag in docs:
            filename = sys.path[0] + '/aiml/so-' + tag.encode('utf-8') + '.aiml'
            f = open(filename, "wb")
            f.write(docs[tag].toprettyxml("  "))
            f.close()
    elif action == 'generate-srai':
        print 'Generating AIML file with Symbolic Reductions in "aiml/so-srai.aiml"'
        saveQuestionStarts(limit=50)
    elif action == 'help':
        print 'Please insert one of the following'
        print ' -a generate-aiml'
        print ' -a generate-srai'
        print ' -a stem-questions'

if __name__ == "__main__":
    main()

# http://imgur.com/gHTG7
# >>> import nltk
# >>> from nltk.corpus import PlaintextCorpusReader
# >>> corpus_root = '/home/text'
# >>> wl = PlaintextCorpusReader(corpus_root, '.*')
# >>> wl.fileids()
# ['_.net.txt', 'ajax.txt', 'android.txt', 'asp.net.txt', 'c#.txt', 'c++.txt', 'c.txt', 'css.txt', 'django.txt', 'git.txt', 'html.txt', 'iphone.txt', 'java.txt', 'javascript.txt', 'jquery.txt', 'json.txt', 'linux.txt', 'mysql.txt', 'perl.txt', 'php.txt', 'python.txt', 'ruby-on-rails.txt', 'sql.txt', 'wordpress.txt']
# >>> cfd = nltk.ConditionalFreqDist(
# ...     (target, fileid[:4])
# ...     for fileid in wl.fileids()
# ...     for w in wl.words(fileid)
# ...     for target in ['.net', 'ajax', 'android', 'asp.net', 'c#', 'c++', 'c', 'css', 'django', 'git', 'html', 'iphone', 'java', 'javascript', 'jquery', 'json', 'linux', 'mysql', 'perl', 'php', 'python', 'ruby', 'sql', 'wordpress']
# ...     if w.lower().startswith(target))
# >>> cfd.plot()

""" Get the most popular ways to start a question from the database, by selecting the first 2 words from all sentences.
    Then group by these 2 words and order from higher to lower count.
    Create aiml-sr.aiml file with all these, by re-applying the templates, without the first 2 words of course:
    <category>
        <pattern>HOW TO *</pattern>
        <template>
            <srai><star/></srai>
        </template>
    </category>
    What might be best to do in this situation actually is to get all the questions, run them through the stemmer
    and save them in a new table, say stem_question[id, title]
    Then run the query below on the stemmed questions. Why? Well this way we ensure we remove all the cases with
    's, or '-' (hyphens) as the second word, etc.
    
    SELECT count( id ) AS cnt, SUBSTRING_INDEX( LOWER( title ) , ' ', 2 ) AS first_words
    FROM stem_question
    GROUP BY first_words
    HAVING cnt > 1
    ORDER BY cnt DESC

    The user input will obviously need to go through the same stemmer to be able to accuratly match it with a question.
    Not necesarilly actually! Why? If only the question titles are ran through the stemmer to get the first two words,
    they are likely to 'root' words anyway.
    Alternatively, instead of putting them through a stemmer, we could just run them through a regex expression 
    to fetch [a-zA-Z] and maybe other symbols such as '.#@' and so on.

    The problem with putting the user input through a stemmer is that we can't use the rest of the AIML set unless we 
    run all those files through the stemmer as well. This might be doable ... but would it be a job too big to do now?

    Get identical questions???
    SELECT count(id) as cnt, lower(title) from question group by lower(title) having cnt > 1 order by cnt desc;

    Apparently there are 432 results in the database...
"""
