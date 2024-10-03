import os
from datetime import datetime

import click
from alembic import command
from alembic.config import Config
from flask import Flask, jsonify, request
from flask.cli import with_appcontext

from enpoints import (endpoint_author_similarity_score,
                      endpoint_connected_posts, endpoint_dataframe,
                      endpoint_get_articles, endpoint_get_authors,
                      endpoint_get_content, endpoint_similarity_score,
                      endpoint_specter_clustering)
from utils import create_approach, list_approaches

app = Flask(__name__)

@app.cli.command("db_migrate")
@click.option("--message", default=None, help="Revision message")
@with_appcontext
def db_migrate(message):
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=True)

@app.cli.command("db_upgrade")
@with_appcontext
def db_upgrade():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


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

@app.route('/api/approaches', methods=['GET'])
def get_approaches():
    limit = request.args.get('limit', default=10, type=int)
    last_spotlight_count = request.args.get('lastSpotlightCount', type=int)
    last_created_at = request.args.get('lastCreatedAt')
    last_id = request.args.get('lastId', type=int)
    filter_type = request.args.get('filter')
    order_by = request.args.get('orderBy', default='spotlights')

    if filter_type not in [None, 'post', 'comment']:
        return jsonify({"error": "Invalid filter type. Use 'post', 'comment', or omit for both."}), 400

    if order_by not in ['spotlights', 'comments', 'recency']:
        return jsonify({"error": "Invalid order_by. Use 'spotlights', 'comments', or 'recency'."}), 400

    if last_created_at:
        last_created_at = datetime.fromisoformat(last_created_at)

    approaches, next_spotlight_count, next_created_at, next_id = list_approaches(
        limit, last_spotlight_count, last_created_at, last_id, filter_type, order_by
    )
    approaches_list = [
        {
            "id": approach[0],
            "main_article": approach[1],
            "node_id": approach[2],
            "link": approach[3],
            "type": approach[4],
            "label": approach[5],
            "created_at": approach[6].isoformat(),
            "spotlight_count": approach[7],
            "spotlights": [
                {
                    "email": spotlight[0],
                    "comment": spotlight[1],
                    "created_at": spotlight[2].isoformat()
                }
                for spotlight in approach[9]
            ]
        }
        for approach in approaches
    ]

    next_params = {}
    if next_spotlight_count is not None:
        next_params = {
            'lastSpotlightCount': next_spotlight_count,
            'lastCreatedAt': next_created_at.isoformat() if next_created_at else None,
            'lastId': next_id
        }

    return jsonify({
        "approaches": approaches_list,
        "nextParams": next_params
    })

@app.route('/api/approaches', methods=['POST'])
def create_new_approach():
    data = request.json
    main_article = data.get('mainArticle')
    node_id = data.get('nodeId')
    link = data.get('link')
    type = data.get('type')
    label = data.get('label')
    comment = data.get('comment')
    email = data.get('email')

    if not node_id or not link:
        return jsonify({"error": "Node ID and link are required"}), 400

    approach_id, new_count, is_spotlight = create_approach(main_article, node_id, link, type, label, email, comment)
    
    return jsonify({
        "success": True, 
        "message": "Approach spotlighted successfully" if is_spotlight else "Approach shared successfully",
        "id": approach_id,
        "spotlight_count": new_count
    }), 201

if __name__ == '__main__':
    app.run(port=5000, debug=True)
