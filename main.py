import os
from flask import Flask, jsonify, request
from utils import create_idea, list_ideas
from enpoints import endpoint_dataframe, endpoint_similarity_score, endpoint_author_similarity_score, endpoint_specter_clustering, endpoint_connected_posts, endpoint_get_authors, endpoint_get_articles, endpoint_get_content

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

@app.route('/api/content', methods=['GET'])
def get_content():
    return jsonify({
        'data': endpoint_get_content()
    })


@app.route('/api/dataframe', methods=['GET'])
def get_dataframe():
    params = request.args.to_dict(flat=False)

    columns = []
    ascendings = []

    for key, value in params.items():
        if key.startswith('columns[') and key.endswith(']'):
            name = key[8:-1]
            columns.append(name)
            ascendings.append(value[0] == 'asc')

    try:
        data = endpoint_dataframe(columns, ascendings)
        return jsonify(data)
    except:
        return []

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

@app.route('/api/ideas', methods=['POST'])
def create_new_idea():
    data = request.json
    article = data.get('article')
    description = data.get('description')
    email = data.get('email')

    if not article or not description:
        return jsonify({"error": "Article and description are required"}), 400

    create_idea(article, description, email)
    return jsonify({"message": "Idea created successfully"}), 201

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    ideas = list_ideas()
    ideas_list = [
        {
            "id": idea[0],
            "article": idea[1],
            "description": idea[2],
            "email": idea[3],
            "created_at": idea[4].isoformat()
        }
        for idea in ideas
    ]
    return jsonify(ideas_list)


if __name__ == '__main__':
    app.run(port=5000, debug=True)
