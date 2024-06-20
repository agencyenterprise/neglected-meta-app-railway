from flask import Flask, jsonify, request
from enpoints import endpoint_dataframe;

app = Flask(__name__)

@app.route('/api/dataframe', methods=['GET'])
def get_dataframe():
    print('[endpoint_dataframe]')
    print(request.args.to_dict(flat=True))



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

if __name__ == '__main__':
    app.run(port=5000, debug=True)
