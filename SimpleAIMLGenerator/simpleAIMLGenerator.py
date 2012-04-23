#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Small script that fetches all text from the database (Q&A) and saves it
as AIML files so it can be used with PyAIML.
"""

import sys, MySQLdb, nltk, marshal
from BeautifulSoup import BeautifulSoup
from xml.dom.minidom import Document

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

# dictionary containing all Q&A
_questions = [] # Format: {'question': [id, title, body, tags], 'answer': [id, body] }
# list of tags used to crawl Stack Overflow, from SOcrawler
tag_list = set(['c#', 'java', 'php', 'javascript', 'jquery', 'android', 'iphone', 'c++', 'asp.net', '.net', 'python', 'mysql', 'html', 'sql', 'ruby-on-rails', 'css', 'ajax', 'linux', 'django', 'json', 'perl', 'git', 'wordpress', 'c'])

# Database connection
try:
    _db = MySQLdb.connect(host = 'localhost',
                          user = 'crawler',
                          passwd = 'crawlpass12',
                          db = 'socrawler')
except MySQLdb.Error, e:
    log("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

def getQuestions():
    global _questions
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
        LIMIT 0,2
        """)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))
    
    while (1):
        row = c.fetchone()
        if row == None:
            break

        item = {
            'questionID': row[0], 
            'question': strip(row[1]), 
            'questionBody': strip(row[2]), 
            'tags': row[3],
            'answerID': row[4], 
            'answer': strip(row[5])
        }
        _questions.append(item)

def writeStemmedQuestions():
    global _db
    c = _db.cursor()
    i = _db.cursor()

    porter = nltk.PorterStemmer()

    try:
        c.execute("""
        SELECT 
            question.id AS questionID,
            question.title AS question, 
            question.tags AS tags 
        FROM question
        ORDER BY question.id ASC
        # LIMIT 0,100000
        """)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))
    
    while (1):
        row = c.fetchone()
        if row == None:
            break

        qid = row[0]
        question = row[1]
        tags = row[2]
        tokens = nltk.word_tokenize(question)
        stemmed_question = [porter.stem(t) for t in tokens]
        question = ' '.join(stemmed_question)
        print str(qid) + ': ' + question
        try:
            i.execute("""
            INSERT INTO stemmed_question (id, stemmed_question, tags)
            VALUES (%s, %s, %s)
            """, (qid, question, tags))
        except MySQLdb.Error, e:
            log("Error %d: %s" % (e.args[0], e.args[1]))

    i.close()
    # Execute all insert statements
    _db.commit()

def saveQuestionStarts():
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

    min_count = 2
    count = 7
    questions = set([])

    while (count >= min_count):
        # Fetch top 'count' words in stemmed questions
        try:
            c.execute("""
                SELECT count( id ) AS cnt, SUBSTRING_INDEX( LOWER( stemmed_question ) , ' ', %s ) AS first_words
                FROM stemmed_question
                GROUP BY first_words
                HAVING cnt > 1
                ORDER BY cnt DESC
            """, (count))
        except MySQLdb.Error, e:
            log("Error %d: %s" % (e.args[0], e.args[1]))

        while (1):
            row = c.fetchone()
            if row == None:
                break

            question_start = row[1]
            tokens = nltk.word_tokenize(question_start)

            """
            TODO: uppercase the questions

            A way to improve this would be to look through the 
            tokens and see if any of them are not words or letters 
            (example: - , * , ( , ) , etc).
            In these cases, leave the original intact and make a copy 
            that removes them and just leaves the text inside. Maybe 
            this can be done with a regex test??? or a length test???
            """

            questions.add(question_start)
            print question_start + ' ::: ' + str(tokens)
        count -= 1

    # save questions starts in file (marshal dump)
    filename = sys.path[0] + '/question_starts.sess'
    qs = file(filename, "wb")
    marshal.dump(questions, qs)
    qs.close()
    saveAimlQuestionStart(questions)

def saveAimlQuestionStart(questions):
    doc = Document()
    # create the root tag
    aiml = doc.createElement("aiml")
    aiml.setAttribute("version", "1.0")
    doc.appendChild(aiml)

    template = doc.createElement("template")
    srai = doc.createElement("srai")
    star = doc.createElement("star")
    srai.appendChild(star)
    template.appendChild(srai)

    for q in questions:
        # initialize the elements required in AIML
        category = doc.createElement("category")
        pattern = doc.createElement("pattern")
        pattern_text = q + ' * '
        pattern.appendChild(doc.createTextNode(pattern_text))
        category.appendChild(pattern)
        category.appendChild(template)
        aiml.appendChild(category)

    # save aiml to file
    filename = sys.path[0] + '/aiml/srai.aiml'
    f = open(filename, 'a+')
    f.write(doc.toprettyxml("  "))
    f.close()

if __name__ == "__main__":

    # writeStemmedQuestions()

    saveQuestionStarts()

    # getQuestions()
    

    # for item in _questions:
    #     tags = set(eval(item['tags'].encode('utf-8')))

    #     # intersect the row's tags with the tags from crawler, to only get the common used ones
    #     tags_to_use = tag_list & tags
    #     if len(tags_to_use) == 0:
    #         tags_to_use = ['unknown']

    #     # Get the data for each Q&A
    #     question = item['question'].encode('utf-8')

    #     for tag in tags_to_use:
    #         # check if the first char in tag is '.' and prepend '_' if so
    #         # that's because '.<name>' files are hidden by default ...
    #         if tag[0] == '.':
    #             tag = '_' + tag.encode('utf-8')
    #         filename = sys.path[0] + '/aiml/' + tag.encode('utf-8') + '.aiml'
    #         # And append that data in multiple files according to the tags associated
    #         # saveFile(data, filename)



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
