from jason import JsonFactory, load_template


docs = 1
a_dict = load_template("./templates/example-template.json")

for i in range(0, docs):
    print("generating {}".format(i))
    print("\n")
    jay = JsonFactory(a_dict)
    jay.persist()
