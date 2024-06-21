from flask import Flask, jsonify, request
from enpoints import endpoint_dataframe, endpoint_similarity_score, endpoint_author_similarity_score;

app = Flask(__name__)

@app.route('/api/dataframe', methods=['GET'])
def get_dataframe():
    params = request.args.to_dict(flat=False)

    columns = []
    ascendings = []

    for key, value in params.items():
        if key.startswith('column[') and key.endswith(']'):
            name = key[7:-1]
            columns.append(name)
            ascendings.append(value[0] == 'asc')


    data = endpoint_dataframe(columns, ascendings)
    return jsonify(data)

@app.route('/api/similarity-score', methods=['GET'])
def get_similarity_score():
    params = request.args.to_dict(flat=False)
    article_list = params.get('article_list[]')
    compared_authors = params.get('compared_authors[]')
    author_pair1 = params.get('author_pair1[]')
    author_pair2 = params.get('author_pair2[]')

    return jsonify({
        'authors': endpoint_author_similarity_score(
            author_pair1,
            author_pair2
        ).tolist(),
        'articles': endpoint_similarity_score(article_list, compared_authors)
    })


if __name__ == '__main__':
    app.run(port=5000, debug=True)
