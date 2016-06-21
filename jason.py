from settings import SETTINGS

import couchdb

from json import load, dumps
from pprint import pformat
from random import getrandbits, choice, randint, uniform
from datetime import timedelta, datetime
from os import path
from glob import glob
from mimetypes import guess_type
from uuid import uuid4
from copy import copy


def load_template(template):
    with open(template) as tmpl_file:
        a_dict = load(tmpl_file)
        return a_dict


class JsonFactory(object):
    # TODO
    # attachment
    # @i || $i
    # magic 0, !
    # book -> ref, assets, index iteration -> var, self ref, annex: text/plain
    # ~range arrays
    # path[1]
    # non random refs
    # hyperlinks as paths
    # !choice mandatory
    # multiple templatevars
    # custom lists
    # vars: @rand_currency, @rand_country, @mime_type, @latlong

    def __init__(self, template, doc_id=None):
        self.SETTINGS = SETTINGS
        self.LISTS = self.load_lists()

        self.template = template

        # remember the lenght of every populated list
        self.list_counts = {}

        # remember operation that can only be done after persist
        self.post_queue = {"attachments": [], "counts": []}

        self.messages = {"attachments": [], "created": []}

        self.CDB = None
        #  try to obtain couchdb target db from the template
        try:
            self.cdb_db_name = template["@couchdb_db"]
        except KeyError:
            self.cdb_db_name = None

        # doc_id == cdb_doc["_id"] == pjson["_id"]
        if doc_id:
            self.doc_id = doc_id
        else:
            self.doc_id = self.gen_uuid()

        self.cdb_doc = None
        self.cdb_doc_url = None
        self.cdb_doc_futon_url = None
        self.cdb_doc_attachment_url = None

        self.is_persisted = False

        self.pjson = self.populate_dict(self.template)

    def __str__(self):
        return pformat(self.pjson)

    __repr__ = __str__

    ascii_art = """
           /$$  /$$$$$$$  /$$$$$$  /$$$$$$$
          |__/ /$$_____/ /$$__  $$| $$__  $$
           /$$|  $$$$$$ | $$  \ $$| $$  \ $$
          | $$ \____  $$| $$  | $$| $$  | $$
          | $$ /$$$$$$$/|  $$$$$$/| $$  | $$
          | $$|_______/  \______/ |__/  |__/
     /$$  | $$
    |  $$$$$$/
     \______/
    """

    # available value template vars
    VALUE_TMPL_VARS = ["@uuid",
                       "@md5",
                       "@url",
                       "@choice_str",
                       "@choice_int",
                       "@choice_float",
                       "@range_int",
                       "@range_float",
                       "@rand_int",
                       "@rand_float",
                       "@rand_bool",
                       "@datetime",
                       "@first_name",
                       "@last_name",
                       "@name_female",
                       "@name_male",
                       "@name_affix",
                       "@name",
                       "@email",
                       "@phone",
                       "@lorem",
                       "@title",
                       "@rand_attachment",
                       "@count_lists",
                       "@index"]

    # available key template vars
    KEY_TMPL_VARS = ["@couchdb_db",
                     "@ref_list_exact",
                     "@ref_list",
                     "@ref_dict_exact",
                     "@ref_dict_rand",
                     "@ref_dict",
                     "@ref_list",
                     "@iteration_list"]

    def print_messages(self):
        """
        print all messages in self.messages
        """
        for k, v in self.messages.items():
            for msg in v:
                if k == "created":
                    self.color_print(msg, "green")
                elif k == "attachments":
                    self.color_print(msg, "magenta")

    def color_print(self, msg, color):
        """
        colorful output
        """
        colors = {"clear": "\033[0;m",
                  "gray": "\033[1;30m",
                  "red": "\033[1;31m",
                  "green": "\033[1;32m",
                  "yellow": "\033[1;33m",
                  "blue": "\033[1;34m",
                  "magenta": "\033[1;35m",
                  "cyan": "\033[1;36m",
                  "white": "\033[1;37m",
                  "crimeson": "\033[1;38m",
                  "red2": "\033[1;41m",
                  "green2": "\033[1;42m",
                  "brown": "\033[1;43m",
                  "blue2": "\033[1;44m",
                  "magenta2": "\033[1;45m",
                  "cyan_hl": "\033[1;46m",
                  "gray_hl": "\033[1;47m",
                  "crimson_hl": "\033[1;48m"}

        print("{}{}{}{}".format(colors["clear"], colors[color], msg, colors["clear"]))

    def load_json(self, f_path):
        """
        read a json file return a dict
        """
        with open(f_path) as jf:
            a_dict = load(jf)

            return a_dict

    def load_lists(self):
        """
        collect *.json in ./lists and concat them to one list
        usable as @choice_str targets eg '@choice_str {listname}'
        list syntax:
            {'listname': ['some', 'entries']}
        """
        f_path = "./lists/"
        lists = {}
        for filename in glob(path.join(f_path, "*.json")):
            a_json = self.load_json(filename)
            for k, v in a_json.items():
                lists[k] = v

        return lists

    def load_attachments(self):
        """
        collect files in ./attachments by file extension
        """
        image_attachments = []
        audio_attachments = []
        video_attachments = []
        f_path = "./attachments/"

        image_extensions = ["jpg", "png", "gif"]
        audio_extensions = ["mp3"]
        video_extensions = ["mp4"]
        image_patterns = []
        audio_patterns = []
        video_patterns = []

        # use upper and lowercase versions of each extension
        for ie in image_extensions:
            image_patterns.append("*.{}".format(ie.lower()))
            image_patterns.append("*.{}".format(ie.upper()))
        for ae in audio_extensions:
            audio_patterns.append("*.{}".format(ae.lower()))
            audio_patterns.append("*.{}".format(ae.upper()))
        for ve in video_extensions:
            video_patterns.append("*.{}".format(ve.lower()))
            video_patterns.append("*.{}".format(ve.upper()))

        extensions = {"image": image_patterns,
                      "audio": audio_patterns,
                      "video": video_patterns}

        for k, v in extensions.items():
            if k == "image":
                for ex in v:
                    for filename in glob(path.join(f_path, ex)):
                        image_attachments.append(filename)
            elif k == "audio":
                for ex in v:
                    for filename in glob(path.join(f_path, ex)):
                        audio_attachments.append(filename)
            elif k == "video":
                for ex in v:
                    for filename in glob(path.join(f_path, ex)):
                        video_attachments.append(filename)

        attachments = {"image": image_attachments,
                       "audio": audio_attachments,
                       "video": video_attachments}

        return attachments

    def get_keypaths(self, a_dict, target_key):
        """
        build the keypaths for a target_key in a_dict

        :param a_dict:
        :param target_key:
        :return: list of path strings
        >>> a_dict = {"my_key": 1, "a_list": [{"nothing": "here"}, {"a_dict": {"my_key": 2}}, {"my_key": 3}]}
        >>> SETTINGS['verbose'] = False
        >>> j = JsonFactory(load_template("./templates/example-template.json"))
        >>> j.get_keypaths(a_dict, "my_key")
        ['a_list[].a_dict.my_key', 'a_list[].my_key', 'my_key']
        """
        result_lists = []
        k_path = []

        def get_keypath(a_dict, target_key):
            """
            get a single keypath for a target_key in a_dict
            """
            for k, v in a_dict.items():
                # always remember the path
                if isinstance(v, list):
                    k_path.append("{}[]".format(k))
                else:
                    k_path.append(k)

                if isinstance(v, dict):
                    get_keypath(v, target_key)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            get_keypath(item, target_key)

                if k == target_key:
                    # key found -> store
                    result_lists.append(copy(k_path))

                # done -> flush
                k_path.pop()

        get_keypath(a_dict, target_key)

        # join the lists to strings
        result = []
        for rl in result_lists:
            rs = ""
            rs += ".".join(rl)
            result.append(rs)

        return sorted(result)

    def traverse(self, obj, k_path=None, callback=None):
        """
        traverse an arbitrary Python object structure (limited to JSON data
        types), calling a callback function for every element in the structure,
        and inserting the return value of the callback as the new value.
        """
        if k_path is None:
            k_path = []

        if isinstance(obj, dict):
            value = {k: self.traverse(v, k_path + [k], callback) for k, v in obj.items()}
        elif isinstance(obj, list):
            value = [self.traverse(elem, k_path + [[]], callback) for elem in obj]
        else:
            value = obj

        if callback is None:
            return value
        else:
            return callback(k_path, value)

    def traverse_modify(self, obj, target_path, action):
        """
        traverses an arbitrary object structure and where the path matches,
        performs the given action on the value, replacing the node with the
        action's return value.
        """
        target_path = self.to_path(target_path)

        def transformer(k_path, value):
            """
            execute the callback onto the value
            """
            if k_path == target_path:
                return action(value)
            else:
                return value

        return self.traverse(obj, callback=transformer)

    # TODO move to traverse_modify
    def to_path(self, k_path):
        """
        helper function, converting path strings into path lists.

        >>> SETTINGS['verbose'] = False
        >>> j = JsonFactory(load_template("./templates/example-template.json"))
        >>> j.to_path('foo')
        ['foo']
        >>> j.to_path('foo.bar')
        ['foo', 'bar']
        >>> j.to_path('foo.bar[]')
        ['foo', 'bar', []]
        """
        if isinstance(k_path, list):
            return k_path  # already in list format

        def _iter_path(k_path):
            for parts in k_path.split('[]'):
                for part in parts.strip('.').split('.'):
                    yield part
                yield []

        return list(_iter_path(k_path))[:-1]

    def persist(self):
        """
        wright the populated dict (pjson) to CouchDB and perform post persist operations
        """
        p_backend = self.get_setting("persistence")
        if p_backend == "couchdb":
            cdb = self.get_cdb()
            try:
                db = cdb[self.cdb_db_name]
            except:
                db = cdb.create(self.cdb_db_name)

            # post processing before persistence
            to_count = self.post_queue["counts"]
            for count in to_count:
                for key_path in self.get_keypaths(self.pjson, count["key"]):
                    # update key_path with count value
                    self.pjson = self.traverse_modify(self.pjson, key_path, self.gen_count_list)

            # persist
            doc_id = self.doc_id
            db[doc_id] = self.pjson

            self.cdb_doc = db.get(self.doc_id)

            cdb_info = self.get_setting("couchdb")
            self.cdb_doc_futon_url = "{}/_utils/document.html?{}/{}".format(cdb_info["host"], self.cdb_db_name, self.doc_id)
            self.cdb_doc_url = "{}/{}/{}".format(cdb_info["host"], self.cdb_db_name, self.doc_id)
            msg = "created document: {}".format(self.cdb_doc_futon_url)
            self.messages["created"].append(msg)

            # post processing after persistence
            for attachment in self.post_queue["attachments"]:
                if self.get_setting("verbose"):
                    msg = "adding attachment: {}".format(attachment["value"])
                    self.color_print(msg, "magenta")
                attachment_file = self.gen_rand_attachment_file(attachment["type"])
                self.add_attachment(attachment_file, attachment["value"])
                # self.post_queue["attachments"].remove(attachment)
                # del self.post_queue["attachments"][attachment]

            print("\n")
            self.color_print(self.ascii_art, "red")
            self.color_print(self.__str__(), "cyan")
            self.print_messages()
            self.persisted = True

    def add_attachment(self, a_path, a_filename):
        """
        append an attachment to a persisted document on CouchDB
        """
        mt = guess_type(a_path)[0]
        a_cdb_db = self.get_cdb_db()
        a_cdb_doc = self.get_cdb_doc()

        # with open(a_path) as f:
        with open(a_path, "rb") as f:
            a_cdb_db.put_attachment(a_cdb_doc, content=f, filename=a_filename, content_type=mt)

        # update the object
        attachments = a_cdb_db[self.doc_id]["_attachments"]
        attachment = attachments[a_filename]
        self.pjson["_attachments"] = attachments
        self.cdb_doc["_attachments"] = attachments
        self.cdb_doc_attachment_url = "{}/{}".format(self.cdb_doc_url, a_filename)
        msg = "appended attachment: {}, {}".format(self.cdb_doc_attachment_url, attachment)
        self.messages["attachments"].append(msg)

    def decide_optional(self):
        """
        decide based on the optional_rate if an optional key-value-pair should be created
        """
        if uniform(0.1, 1.0) <= self.get_setting("optional_rate"):
            return True
        else:
            return False

    # -------------------------------------------------------------------------
    # setters -----------------------------------------------------------------
    # -------------------------------------------------------------------------

    def set_list_count(self, a_list, a_key):
        """
        increase the list count for a_list.
        Append to an existing or create a new entry
        """
        if a_key in self.list_counts:
            self.list_counts[a_key] = self.list_counts[a_key] + len(a_list)
        else:
            self.list_counts[a_key] = len(a_list)

    # -------------------------------------------------------------------------
    # getters -----------------------------------------------------------------
    # -------------------------------------------------------------------------

    def get_tmpl_vars(self, v, scope):
        """
        read the template vars from a string base on scope (key || value)
        """
        if scope == "value":
            gtvs = self.VALUE_TMPL_VARS
        elif scope == "key":
            gtvs = self.KEY_TMPL_VARS

        tmpl_vars = []
        # TODO bug a_tvar can never be found if a_tv is also a tv
        for tmpl_var in gtvs:
            if v.find(tmpl_var) != -1:
                tmpl_vars.append(tmpl_var)

        return tmpl_vars

    def get_param_list(self, a_str):
        """
        read all params {p1 | p2} in a_str
        """
        param_list = []
        param_str = ""
        if "{" in a_str and "}" in a_str:
            param_str = a_str[a_str.find("{")+1:a_str.find("}")]
            token = "|"
            if param_str.find(token) != -1:
                param_list = param_str.split(token)
            else:
                param_list.append(param_str)

        return [item.strip() for item in param_list]

    def get_cdb(self):
        """
        return a CouchDB instance or create one if none exists
        """
        if not self.CDB:
            host = self.get_setting("couchdb")["host"]
            user = self.get_setting("couchdb")["user"]
            pw = self.get_setting("couchdb")["password"]

            self.CDB = couchdb.Server(host)
            self.CDB.resource.credentials = (user, pw)

        return self.CDB

    def get_cdb_db(self):
        """
        return a CouchDB Database instance
        """
        db_name = self.cdb_db_name
        return self.get_cdb()[db_name]

    def get_cdb_doc(self):
        """
        return the persisted CouchDB document
        """
        doc_id = self.doc_id
        return self.get_cdb_db()[doc_id]

    def get_setting(self, a_key):
        """
        return a setting value by a_key
        """
        return self.SETTINGS[a_key]

    def get_list(self, a_key):
        """
        return a list by a_key
        """
        return self.LISTS[a_key]

    def get_count_list(self, a_key):
        """
        return the count of a list by a_key
        """
        return self.list_counts[a_key]

    # -------------------------------------------------------------------------
    # generators --------------------------------------------------------------
    # -------------------------------------------------------------------------

    def gen_rand_attachment_file(self, attachment_type):
        """
        return a random attachment by attachment_type
        """
        available_attachments = self.load_attachments()[attachment_type]
        return choice(available_attachments)

    def gen_url(self, a_str):
        """
        return a random url
        """
        adjectives = self.get_list("adjective")
        nouns = self.get_list("noun")
        sugar = "{}-{}".format(choice(adjectives), choice(nouns))

        param = self.get_param_list(a_str)
        known_sites = {"facebook": "https://www.facebook.com/",
                       "google+": "https://plus.google.com/",
                       "twitter": "https://twitter.com/"}
        if len(param) > 0 and param[0] in known_sites:
            base_url = known_sites[param[0]]

            return base_url + sugar
        else:
            return "https://{}.com".format(sugar)

    def gen_choice_str(self, a_str):
        """
        choose a string from given choices
        """
        params = self.get_param_list(a_str)
        if len(params) == 1:
            # assume a list
            choices = self.get_list(params[0])
        else:
            choices = params

        return choice(choices)

    def gen_choice_int(self, a_str):
        """
        choose an int from given choices
        """
        choices = self.get_param_list(a_str)
        a_choice = choice(choices)

        return int(a_choice)

    def gen_choice_float(self, a_str):
        """
        choose an float from given choices
        """
        choices = self.get_param_list(a_str)
        a_choice = choice(choices)

        return float(a_choice)

    def gen_range_int(self, a_str):
        """
        choose an int within a given range
        """
        a_range = self.get_param_list(a_str)
        mini = int(a_range[0])
        maxi = int(a_range[1])

        return randint(mini, maxi)

    def gen_range_float(self, a_str):
        """
        choose an float from a given range
        """
        a_range = self.get_param_list(a_str)
        mini = float(a_range[0])
        maxi = float(a_range[1])

        return uniform(mini, maxi)

    def gen_lorem(self):
        """
        return a random lorem ipsum from lists
        """
        choices = self.get_list("lorem")

        return choice(choices)

    def get_title(self):
        """
        return a string with the scheme {adjective noun}
        """
        adjective = choice(self.get_list("adjective"))
        noun = choice(self.get_list("noun"))

        return "{} {}".format(adjective, noun)

    def gen_first_name(self, gender="all"):
        """
        return a first name by gender
        """
        men = self.get_list("male_name")
        women = self.get_list("female_name")

        if gender == "all":
            names = men + women
        elif gender == "female":
            names = women
        elif gender == "male":
            names = men
        name = choice(names)

        return name

    def gen_last_name(self):
        """
        return a last name
        """
        names = self.get_list("last_name")
        return choice(names)

    def gen_name(self):
        """
        return a full name
        """
        name = "{} {}".format(self.gen_first_name(), self.gen_last_name())

        return name

    def gen_name_affix(self):
        """
        return a name affix like Prof.
        """
        # TODO always optional?
        nas = self.get_list("name_affix")

        return choice(nas)

    def gen_phone(self):
        """
        return a phone number with a dash of randomness
        """
        if bool(getrandbits(1)):
            nr = "+49 "
        else:
            nr = "0"
        for pos in range(0, randint(10, 20)):
            nr = nr + str(randint(0, 9))

        return nr

    def gen_email(self):
        """
        return a email adress with a dash of randomness
        """
        providers = ["gmail.com", "web.de", "gmx.de", "mailbox.org"]
        provider = choice(providers)
        email = "{}.{}@{}".format(self.gen_first_name().lower(), self.gen_last_name().lower(), provider)

        return email

    def gen_rand_bool(self):
        """
        return True or False 50:50
        """
        return bool(getrandbits(1))

    def gen_rand_int(self, mini=0, maxi=100):
        """
        return an int within mini and maxi
        """
        return randint(mini, maxi)

    def gen_rand_float(self, mini=0.0, maxi=100.0):
        """
        return a float within mini and maxi
        """
        return uniform(mini, maxi)

    def gen_datetime(self, delta=0):
        """
        return a datetime string in the format:
        2015-12-13T12:16:17.396927Z
        """
        now = datetime.utcnow()
        delta = timedelta(days=delta)
        a_datetime = now + delta

        return a_datetime.isoformat() + "Z"

    def gen_uuid(self):
        """
        return a 32 digit uuid string eg:
        0648e6344bcd4138acafab7c28b0bad9
        """
        uuids_from = self.get_setting("uuids")
        if uuids_from == "python":
            return uuid4().hex
        elif uuids_from == "couchdb":
            return self.get_cdb().uuids()[0]

    def gen_md5(self):
        """
        return a 32 digit md5 hashsum string eg:
        a3cca2b2aa1e3b5b3b5aad99a8529074
        """
        # implement
        return "a3cca2b2aa1e3b5b3b5aad99a8529074"

    def gen_iteration_list(self, a_key, a_value):
        """
        return a populated list
        if @index is in the values insert len(list) as value
        "@iteration_list {my_k | 2}": ["@name"]
            -> ["Justin Case", "Peter Parker"]
        """
        params = self.get_param_list(a_key)
        # target_key = params[0]
        iterations = int(params[1])
        nv = []
        while len(nv) < iterations:
            nv_candidate = self.populate(a_key, a_value[0])
            # TODO! prevent deadlocks

            # @index fix
            # TODO proper implement this
            if nv_candidate not in nv:
                if isinstance(nv_candidate, dict):
                    for k, v in nv_candidate.items():
                        if v == "@index":
                            nv_candidate[k] = len(nv)
                nv.append(nv_candidate)

        return nv

    def gen_count_list(self, a_value):
        """
        used as callback for traverse_modify
        """
        count_target = self.get_param_list(a_value)[0]
        return self.get_count_list(count_target)

    def gen_ref_dict(self, a_key, a_value):
        """
        return a dict reference from another CouchDB document
        """
        subset = {}
        db_name = a_value["db"]
        couch_doc_id = a_value["doc_id"]
        keys = a_value["keys"]

        cdb = self.get_cdb()
        db = cdb[db_name]
        couch_doc = db.get(couch_doc_id)

        for item in keys:
            if item in couch_doc:
                subset[item] = couch_doc[item]

        # TODO check result, use traverse
        return subset

    def gen_ref_dict_exact(self, a_key, a_value):
        """
        return a dict reference from another CouchDB document
        """
        db_name = a_value["db"]
        couch_doc_id = a_value["doc_id"]
        target_key = a_value["key"]

        cdb = self.get_cdb()
        db = cdb[db_name]
        couch_doc = db.get(couch_doc_id)

        # TODO check result, use traverse
        return couch_doc[target_key]

    def gen_ref_dict_rand(self, a_key, a_dict):
        """
        return a random dict reference from another CouchDB document
        """
        subset = {}
        db_name = a_dict["db"]
        keys = a_dict["keys"]

        cdb = self.get_cdb()
        db = cdb[db_name]
        ads = db.view("_all_docs")
        rnd = randint(0, len(ads) - 1)
        # TODO get random doc without this dumb shit
        for i, d in enumerate(db):
            if i == rnd:
                doc_id = d
        a_doc = db[doc_id]
        for item in keys:
            if item in a_doc:
                subset[item] = a_doc[item]

        return subset

    def gen_ref_list(self, a_key, a_dict):
        """
        return a list reference from another CouchDB document
        """
        def dict_in_list(a_dict, a_list):
            """
            check if a_list already contains a_dict
            """
            def dict_equals_dict(dict_a, dict_b):
                """
                check if all key-value-pairs of dict_a and dict_b are equal
                """
                return True if dumps(dict_b, sort_keys=True) is dumps(dict_b, sort_keys=True) else False

            return True if any(dict_equals_dict(a_dict, list_dict) for list_dict in a_list) else False

        results = []
        while len(results) <= a_dict["amount"]:
            # TODO! avoid deadlocks here
            result_candidate = self.gen_ref_dict_rand(a_key, a_dict)
            print(result_candidate)

            if not dict_in_list(result_candidate, results):
                results.append(result_candidate)

        return results

    # -------------------------------------------------------------------------
    # populators --------------------------------------------------------------
    # -------------------------------------------------------------------------

    def populate_list(self, k, a_list):
        """
        populate a dict value of the list type
        """
        p_list = []
        tvs = self.get_tmpl_vars(k, "key")
        if not tvs:
            # no template vars
            for v in a_list:
                p_list.append(self.populate(k, v))

        self.set_list_count(p_list, k)

        return p_list

    def populate_str(self, a_key, a_str):
        """
        populate a dict value of the string type
        """
        tvs = self.get_tmpl_vars(a_str, "value")
        if not tvs:
            # no template vars
            return a_str

        # todo get params here and pass them
        # tps = self.get_param_list(a_str)

        # TODO check if len==1
        tv = tvs[0]
        if tv == "@couchdb_db":
            # skip -> constructor already read it
            pass
        elif tv == "@uuid":
            return self.gen_uuid()
        elif tv == "@md5":
            return self.gen_md5()
        elif tv == "@url":
            return self.gen_url(a_str)
        elif tv == "@choice_str":
            return self.gen_choice_str(a_str)
        elif tv == "@choice_int":
            return self.gen_choice_int(a_str)
        elif tv == "@choice_float":
            return self.gen_choice_float(a_str)
        elif tv == "@range_int":
            return self.gen_range_int(a_str)
        elif tv == "@range_float":
            return self.gen_range_float(a_str)
        elif tv == "@rand_int":
            return self.gen_rand_int()
        elif tv == "@rand_float":
            return self.gen_rand_float()
        elif tv == "@rand_bool":
            return self.gen_rand_bool()
        elif tv == "@datetime":
            # TODO future past
            return self.gen_datetime()
        elif tv == "@first_name":
            return self.gen_first_name()
        # can be done via choice_str
        elif tv == "@last_name":
            return self.gen_last_name()
        elif tv == "@name_female":
            return self.gen_first_name("female")
        elif tv == "@name_male":
            return self.gen_first_name("male")
        elif tv == "@name_affix":
            return self.gen_name_affix()
        elif tv == "@name":
            return self.gen_name()
        elif tv == "@email":
            return self.gen_email()
        elif tv == "@phone":
            return self.gen_phone()
        elif tv == "@lorem":
            return self.gen_lorem()
        elif tv == "@title":
            return self.get_title()
        elif tv == "@count_lists":
            # remember for post processing
            self.post_queue["counts"].append({"key": a_key, "value": a_str})
            return a_str
        elif tv == "@rand_attachment":
            attachment_id = self.gen_uuid()
            param = self.get_param_list(a_str)[0]
            # remember for post processing
            self.post_queue["attachments"].append({"key": a_key, "value": attachment_id, "type": param})
            return attachment_id
        else:
            return a_str

    def populate(self, k, v):
        """
        switch for the value types
        """
        # non magic-types
        nmt = (int, float, bool)

        if isinstance(v, str):
            return self.populate_str(k, v)
        elif isinstance(v, list):
            return self.populate_list(k, v)
        elif isinstance(v, dict):
            return self.populate_dict(v)
        elif isinstance(v, nmt):
            return v
        else:
            return None

    def populate_dict(self, a_dict):
        """
        populate a dict
        """
        p_dict = {}

        for k in a_dict:
            v = a_dict[k]
            t = type(a_dict[k])

            # TODO check key tmpl vars
            if k[0] == "?":
                # optional: decide if we create it
                if self.decide_optional():
                    nv = self.populate(k, v)
                    p_dict[k[1:]] = nv
                else:
                    nv = "optional not created"
            else:
                # check key template vars
                tvl = self.get_tmpl_vars(k, "key")
                if tvl:
                    tv = tvl[0]
                    # print("processing {}: {}".format(tv, v))
                    if tv == "@iteration_list":
                        params = self.get_param_list(k)
                        target_key = params[0]
                        nv = self.gen_iteration_list(k, v)

                        self.set_list_count(nv, target_key)

                        p_dict[target_key] = nv
                    elif tv == "@ref_dict":
                        nv = self.gen_ref_dict(k, v)

                        result_key = v["result_key"]
                        p_dict[result_key] = nv
                    elif tv == "@ref_dict_rand":
                        nv = self.gen_ref_dict_rand(k, v)

                        result_key = v["result_key"]
                        p_dict[result_key] = nv
                    elif tv == "@ref_dict_exact":
                        nv = self.gen_ref_dict_exact(k, v)

                        result_key = v["result_key"]
                        p_dict[result_key] = nv
                    elif tv == "@ref_list":
                        nv = self.gen_ref_list(k, v)

                        result_key = v["result_key"]
                        p_dict[result_key] = nv
                else:
                    nv = self.populate(k, v)
                    p_dict[k] = nv

                if self.get_setting("verbose"):
                    msg = "key: {}, type: {}, value: {} -> {}".format(k, t, v, nv)
                    self.color_print(msg, "white")

        return p_dict
