# encoding: utf-8

import re
import time
import json
import pynlpir
import datetime
import threading
from gensim import models
from gensim import corpora


def get_corpus():
    names = []
    contents = []
    path = "./input/bd_top3_random10000_sample.json"

    print("reading corpus...")
    start = datetime.datetime.now()
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            dict = json.loads(line)
            if 'name' in dict and 'content' in dict and dict['content']:
                desc = ""
                names.append(dict['name'])
                for item in dict['content']:
                    desc = desc + item['desc'] + "。"
                desc = desc.replace("[", "").replace("]", "").replace("...", "。").replace("\n", "。")
                desc = desc.replace(dict['name'], "")
                contents.append(desc)
    end = datetime.datetime.now()
    print("reading corpus done.")
    print("reading time: {0}s".format((end - start).total_seconds()))

    return names, contents


def get_stopwords():
    stopwords = []
    stopwordstype = set()

    path = "./input/stop_words.txt"
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            stopwords.append(line.strip())

    # path = "./input/district.txt"
    # with open(path, 'r', encoding='utf-8') as f:
    #     lines = f.readlines()
    #     for line in lines:
    #         stopwords.append(line.strip())

    path = "./input/stop_words_type.txt"
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            stopwordstype.add(line.strip())

    return stopwords, stopwordstype


pynlpir.open()
stop_words, stop_words_type = get_stopwords()


def process_text(text):
    lowered = text.lower()

    tokens = pynlpir.segment(lowered, pos_names='child')

    filtered = [word[0] for word in tokens if filter(word)]

    return filtered


def filter(word):
    useful_word_pattern = u"^[a-zA-Z0-9\u4e00-\u9fa5]+$"
    useful_word = re.compile(useful_word_pattern)

    district_pattern = u"[\u4e00-\u9fa5]{1,7}?(?:省|自治区|市|区|县|镇|村|街)$"
    district = re.compile(district_pattern)

    return 1 < len(word[0]) < 10 and useful_word.match(word[0]) and not district.match(word[0]) and \
        word[0] not in stop_words and word[1] not in stop_words_type


lock = threading.Lock()


def process_thread(i, num_thread, corpus, corpus_list):
    while i < len(corpus):
        processed = process_text(corpus[i])
        corpus_list[i] = processed
        i = i + num_thread


def process_corpus(corpus):
    # corpus_list = []
    corpus_list = [None for i in range(len(corpus))]

    threads = []
    num_thread = 5
    print("cutting corpus...")
    start = datetime.datetime.now()

    for i in range(num_thread):
        t = threading.Thread(target=process_thread, args=(i, num_thread, corpus, corpus_list))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # for text in corpus:
    #     corpus_list.append(process_text(text))

    end = datetime.datetime.now()
    print("cutting corpus done.")
    print("cutting time: {0}s".format((end - start).total_seconds()))

    return corpus_list


def tf_idf():
    names, contents = get_corpus()
    corpus = process_corpus(contents)
    del contents
    print("computing TF-IDF...")
    start = datetime.datetime.now()
    dictionary = corpora.Dictionary(corpus)
    corpus_bow = [dictionary.doc2bow(text) for text in corpus]
    del corpus
    id2token = dict(zip(dictionary.token2id.values(), dictionary.token2id.keys()))
    del dictionary
    tfidf_model = models.TfidfModel(corpus_bow)
    end = datetime.datetime.now()
    print("computing TF-IDF done.")
    print("computing time: {0}s".format((end - start).total_seconds()))

    return names, corpus_bow, id2token, tfidf_model


def count_chinese(word):
    count = 0
    for char in word:
        if u'\u4e00' <= char <= u'\u9fa5':
            count = count + 1

    return count


def main():
    filename = "compare_gensim_10000"
    path_output = "./output/results_{}.txt".format(filename)
    path_word = "./output/tokens_{}.txt".format(filename)

    print("started")
    start = datetime.datetime.now()
    names, corpus_bow, id2token, tfidf_model = tf_idf()

    print("writing results...")
    start_file = datetime.datetime.now()
    with open(path_output, 'w', encoding='utf-8') as f:
        for i in range(len(names)):
            f.write("Top words in {0}\n".format(names[i]))
            tfidf = tfidf_model[corpus_bow[i]]
            sorted_tfidf = sorted(tfidf, key=lambda item: item[1], reverse=True)
            for id, score in sorted_tfidf[:10]:
                f.write("\tWord: {0:{2}} TF-IDF: {1:.5f}\n".format(id2token[id], score,
                                                                   10 - count_chinese(id2token[id])))
        end = datetime.datetime.now()
        f.write("Total time: {0}s\n".format((end - start).total_seconds()))
        end_file = datetime.datetime.now()
        print("writing results done.")
        print("writing time: {0}s".format((end_file - start_file).total_seconds()))

    print("writing tokens...")
    with open(path_word, 'w', encoding='utf-8') as f:
        for word in id2token.values():
            f.write(word + "\n")
    print("writing tokens done.")
    print("all done.")


if __name__ == "__main__":
    main()
