from flask import Flask, jsonify, request
from enpoints import endpoint_dataframe, endpoint_similarity_score, endpoint_author_similarity_score, endpoint_specter_clustering, endpoint_connected_posts, endpoint_get_authors, endpoint_get_articles;

app = Flask(__name__)

def is_array_empty(array):
    return array is None or len(array) == 0

@app.route('/api/authors', methods=['GET'])
def get_authors():
    return jsonify({
        'data': endpoint_get_authors()
    })

@app.route('/api/articles', methods=['GET'])
def get_articles():
    return jsonify({
        'data': endpoint_get_articles()
    })

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

    return jsonify(endpoint_dataframe(columns, ascendings))

@app.route('/api/similarity-score', methods=['GET'])
def get_similarity_score():
    params = request.args.to_dict(flat=False)
    article_list = params.get('article_list[]')
    compared_authors = params.get('compared_authors[]')
    author_pair1 = params.get('author_pair1[]')
    author_pair2 = params.get('author_pair2[]')

    articles_result = []

    if(is_array_empty(article_list) == False):
        articles_result = endpoint_similarity_score(article_list, compared_authors)

    return jsonify({
        'authors': endpoint_author_similarity_score(
            author_pair1,
            author_pair2
        ).tolist(),
        'articles': articles_result
    })

@app.route('/api/specter-clustering', methods=['GET'])
def get_specter_clustering():
    n = int(request.args.get('cluster_count'))
    cluster_choice = int(request.args.get('cluster'))
    select_by_content = request.args.get('content')
    return jsonify(endpoint_specter_clustering(n, cluster_choice, select_by_content))

@app.route('/api/connected-posts', methods=['GET'])
def get_connected_posts():
    depth = int(request.args.get('depth'))
    a_name = request.args.get('a_name')
    return jsonify(endpoint_connected_posts(a_name, depth))

if __name__ == '__main__':
    app.run(port=5000, debug=True)
