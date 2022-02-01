import json
import requests
import URLHaus
import pytest
import demistomock as demisto
from CommonServerPython import Common

url_command_test = [
    ('ok', ["test_tag1", "test_tag2"]),
    ('ok', []),
    ('no_results', ["test_tag1", "test_tag2"]),
    ('no_results', []),
    ('invalid_url', ["test_tag1", "test_tag2"]),
]


@pytest.mark.parametrize('query_status,tags', url_command_test)
def test_url_command(mocker, query_status, tags):
    """
        Given
        - An URL.

        When
        - Running url_command with the url.

        Then
        - Validate that the Tags were created
        - Validate that the URL and DBotScore entry context have the proper values.
        - Validate that the relationships were created

    """
    response = requests.models.Response()
    response._content = json.dumps({'query_status': query_status,
                                    "id": "105821",
                                    "urlhaus_reference": "https:\/\/urlhaus.abuse.ch\/url\/105821\/",
                                    "url": "http:\/\/sskymedia.com\/VMYB-ht_JAQo-gi\/INV\/99401FORPO\/20673114777\/US\/Outstanding-Invoices\/",
                                    "url_status": "online",
                                    "host": "sskymedia.com",
                                    "date_added": "2019-01-19 01:33:26 UTC",
                                    "threat": "malware_download",
                                    "tags": tags,
                                    "blacklists": {
                                        "spamhaus_dbl": "not listed",
                                        "surbl": "not listed"
                                    },
                                    "payloads": [
                                        {
                                            "firstseen": "2019-01-19",
                                            "filename": "676860772178.doc",
                                            "file_type": "doc",
                                            "response_size": "172752",
                                            "response_md5": "cf6bc359bc8a667c1b8d241e9591f392",
                                            "response_sha256": "72820698de9b69166ab226b99ccf70f3f58345b88246f7d5e4e589c21dd44435",
                                            "urlhaus_download": "https:\/\/urlhaus-api.abuse.ch\/v1\/download\/72820698de9b69166ab226b99ccf70f3f58345b88246f7d5e4e589c21dd44435\/",
                                            "signature": "Heodo",
                                            "virustotal": {
                                                "result": "18 \/ 58",
                                                "percent": "31.03",
                                                "link": "https:\/\/www.virustotal.com\/file\/72820698de9b69166ab226b99ccf70f3f58345b88246f7d5e4e589c21dd44435\/analysis\/1547876224\/"
                                            }
                                        }]}).encode('utf-8')
    mocker.patch.object(URLHaus, 'query_url_information', return_value=response)
    result = mocker.patch.object(demisto, 'results')
    URLHaus.main()

    context = result.call_args[0][0]['EntryContext']
    URL = context.get('URL(val.Data && val.Data == obj.Data)', {})
    assert 'Data' in URL[0] if query_status == 'ok' or query_status == 'no_results' else 'Data' not in URL
    assert all(elem in URL[0]['Tags'] for elem in tags) if query_status == 'ok' else 'Tags' not in URL
    assert 'Relationships' in URL[0] if query_status == 'ok' else 'Relationships' not in URL
    Dbot_score = context.get(
        'DBotScore(val.Indicator && val.Indicator == obj.Indicator && val.Vendor == obj.Vendor && val.Type == obj.Type)')
    assert Dbot_score[0]['Score'] == 3 if query_status == 'ok' else Dbot_score[0][
                                                                        'Score'] == 0 if query_status == 'no_results' else not Dbot_score


url_command_test_reliability_dbot_score = [
    ('online', (3, "The URL is active (online) and currently serving a payload")),
    ('offline', (2, "The URL is inadctive (offline) and serving no payload")),
    ('unknown', (0, "The URL status could not be determined")),
    ('test_no_status', (1, "The URL is not listed")),
    (None, (1, "The URL is not listed"))
]


@pytest.mark.parametrize('status,excepted_output', url_command_test_reliability_dbot_score)
def test_url_reliability_dbot_score(status, excepted_output):
    """

    Given:
        - Url status from URLhaus database.

    When:
        - Calculating dbot score.

    Then:
        - Successes with right dbot score.

    """

    output = URLHaus.calculate_dbot_score('url', status)
    for i in range(len(excepted_output)):
        assert output[i] == excepted_output[i]


url_command_test_create_payloads = [
    ({'payloads': [{'virustotal': {'percent': 1.23, 'link': 'test_link'},
                    'filename': 'test_file',
                    'file_type': 'test_type',
                    'response_md5': 'test_md5',
                    'response_sha256': 'test_sha256'}]},
     [{
         'Name': 'test_file',
         'Type': 'test_type',
         'MD5': 'test_md5',
         'SHA256': 'test_sha256',
         'VT': {
             'Result': 1.23,
             'Link': 'test_link'
         }
     }]), ({'payloads': []}, []),
    ({}, [])
]


@pytest.mark.parametrize('test_data,excepted_output', url_command_test_create_payloads)
def test_url_create_payloads(test_data, excepted_output):
    """

    Given:
        - Url information including payloads which contain files info.

    When:
        - Creating list of files.

    Then:
        - list of {name,type,md5,sha256,vt}

        """
    assert URLHaus.url_create_payloads(url_information=test_data) == excepted_output


url_command_test_create_blacklists = [
    ({'blacklists': {'test_name_0': 'test_status',
                     'test_name_1': 'test_status'}},
     [{'Name': 'test_name_0',
       'Status': 'test_status'},
      {'Name': 'test_name_1',
       'Status': 'test_status'}
      ]), ({'blacklists': {}}, []),
    ({}, [])
]


@pytest.mark.parametrize('test_data,excepted_output', url_command_test_create_blacklists)
def test_url_create_blacklists(test_data, excepted_output):
    """

    Given:
        - Url information including blacklists which contain name,status.

    When:
        - Creating list of blacklist.

    Then:
        - Return list of {name,status}.

    """

    assert URLHaus.url_create_blacklist(url_information=test_data) == excepted_output


url_command_test_create_relationships = [
    ("127.0.0.1", 'IP', True, 1),
    ("127.0.0.1", 'IP', False, 1),
    ("127.0.0.1", 'IP', True, 22),
    ("127.0.0.1", 'IP', False, 22),
    ("127.0.0.1", 'IP', True, 1000),
    ("127.0.0.1", 'IP', False, 1000),
    ("test_domain.com", 'Domain', True, 1),
    ("test_domain.com", 'Domain', False, 1),
    ("test_domain.com", 'Domain', True, 22),
    ("test_domain.com", 'Domain', False, 22),
    ("test_domain.com", 'Domain', True, 1000),
    ("test_domain.com", 'Domain', False, 1000),
]


@pytest.mark.parametrize('host,host_type,create_relationship,max_num_relationships',
                         url_command_test_create_relationships)
def test_url_command_create_relationships(host, host_type, create_relationship, max_num_relationships):
    """

    Given:
        - Url host, file list, Create relationship table(T/F), max number of relationships(Limited to 1000).

    When:
        - Creating relationships table for url command.

    Then:
        - Return indicators relationships table {Relationship,EntityA,EntityAType,EntityB,EntityBType}.

    """
    files = [{
        'Name': f'test_file{i}',
        'Type': f'test_type{i}',
        'MD5': f'test_md5{i}',
        'SHA256': f'test_sha256{i}',
        'VT': {
            'Result': float(i),
            'Link': f'test_link{i}'
        }
    } for i in range(10000)]
    uri = "test_uri"
    excepted_output = []
    if create_relationship:
        excepted_output = [{
            "Relationship": 'related-to' if host_type == 'IP' else 'hosted-on',
            "EntityA": uri,
            "EntityAType": 'URL',
            "EntityB": host,
            "EntityBType": host_type,
        }]
        excepted_output.extend([{
            "Relationship": 'related-to',
            "EntityA": uri,
            "EntityAType": 'URL',
            "EntityB": files[i].get('SHA256'),
            "EntityBType": 'File',
        } for i in range(max_num_relationships - 1)])
    kwargs = {'create_relationships': create_relationship, 'max_num_of_relationships': max_num_relationships}
    results = URLHaus.url_create_relationships(uri, host, files, **kwargs)
    assert len(results) == len(excepted_output)
    for i in range(len(results)):
        assert results[i].to_context() == excepted_output[i]


#
# domain_command_test = [
#     ('ok', ["test_tag1", "test_tag2"]),
#     ('ok', []),
#     ('no_results', ["test_tag1", "test_tag2"]),
#     ('no_results', []),
#     ('invalid_url', ["test_tag1", "test_tag2"]),
# ]
#
#
# @pytest.mark.parametrize('query_status,tags', domain_command_test)
# def test_domain_command(mocker, query_status, tags):
#     """
#         Given
#         - An URL.
#
#         When
#         - Running url_command with the url.
#
#         Then
#         - Validate that the Tags were created
#         - Validate that the URL and DBotScore entry context have the proper values.
#         - Validate that the relationships were created
#
#     """
#     response = requests.models.Response()
#     response._content = json.dumps({'query_status': query_status,
#                                     "id": "105821",
#                                     "urlhaus_reference": "https:\/\/urlhaus.abuse.ch\/url\/105821\/",
#                                     "url": "http:\/\/sskymedia.com\/VMYB-ht_JAQo-gi\/INV\/99401FORPO\/20673114777\/US\/Outstanding-Invoices\/",
#                                     "url_status": "online",
#                                     "host": "sskymedia.com",
#                                     "date_added": "2019-01-19 01:33:26 UTC",
#                                     "threat": "malware_download",
#                                     "tags": tags,
#                                     "blacklists": {
#                                         "spamhaus_dbl": "not listed",
#                                         "surbl": "not listed"
#                                     },
#                                     "payloads": [
#                                         {
#                                             "firstseen": "2019-01-19",
#                                             "filename": "676860772178.doc",
#                                             "file_type": "doc",
#                                             "response_size": "172752",
#                                             "response_md5": "cf6bc359bc8a667c1b8d241e9591f392",
#                                             "response_sha256": "72820698de9b69166ab226b99ccf70f3f58345b88246f7d5e4e589c21dd44435",
#                                             "urlhaus_download": "https:\/\/urlhaus-api.abuse.ch\/v1\/download\/72820698de9b69166ab226b99ccf70f3f58345b88246f7d5e4e589c21dd44435\/",
#                                             "signature": "Heodo",
#                                             "virustotal": {
#                                                 "result": "18 \/ 58",
#                                                 "percent": "31.03",
#                                                 "link": "https:\/\/www.virustotal.com\/file\/72820698de9b69166ab226b99ccf70f3f58345b88246f7d5e4e589c21dd44435\/analysis\/1547876224\/"
#                                             }
#                                         }]}).encode('utf-8')
#     mocker.patch.object(URLHaus, 'query_url_information', return_value=response)
#     result = mocker.patch.object(demisto, 'results')
#     URLHaus.main()
#
#     context = result.call_args[0][0]['EntryContext']
#     URL = context.get('URL(val.Data && val.Data == obj.Data)', {})
#     assert 'Data' in URL[0] if query_status == 'ok' or query_status == 'no_results' else 'Data' not in URL
#     assert all(elem in URL[0]['Tags'] for elem in tags) if query_status == 'ok' else 'Tags' not in URL
#     assert 'Relationships' in URL[0] if query_status == 'ok' else 'Relationships' not in URL
#     Dbot_score = context.get(
#         'DBotScore(val.Indicator && val.Indicator == obj.Indicator && val.Vendor == obj.Vendor && val.Type == obj.Type)')
#     assert Dbot_score[0]['Score'] == 3 if query_status == 'ok' else Dbot_score[0][
#                                                                         'Score'] == 0 if query_status == 'no_results' else not Dbot_score


domain_command_test_reliability_dbot_score = [
    ({'spamhaus_dbl': 'spammer_domain', 'surbl': 'test'},
     (Common.DBotScore.BAD, "The queried Domain is a known spammer domain")),
    ({'spamhaus_dbl': 'phishing_domain', 'surbl': 'test'},
     (Common.DBotScore.BAD, "The queried Domain is a known phishing domain")),
    ({'spamhaus_dbl': 'botnet_cc_domain', 'surbl': 'test'},
     (Common.DBotScore.BAD, "The queried Domain is a known botnet C&C domain")),
    ({'spamhaus_dbl': 'test', 'surbl': 'listed'},
     (Common.DBotScore.BAD, "The queried Domain is listed on SURBL")),
    ({'spamhaus_dbl': 'not_listed', 'surbl': 'test'},
     (Common.DBotScore.NONE, "The queried Domain is not listed on Spamhaus DBL")),
    ({'spamhaus_dbl': 'test', 'surbl': 'not_listed'},
     (Common.DBotScore.NONE, "The queried Domain is not listed on SURBL")),
    ({'spamhaus_dbl': 'test', 'surbl': 'test'},
     (Common.DBotScore.GOOD, "There is no information about Domain in the blacklist")),
    ({'spamhaus_dbl': 'botnet_cc_domain', 'surbl': 'not_listed'},
     (Common.DBotScore.BAD, "The queried Domain is a known botnet C&C domain")),
    ({'spamhaus_dbl': 'not_listed', 'surbl': 'listed'},
     (Common.DBotScore.BAD, "The queried Domain is listed on SURBL")),
    ({'surbl': 'not_listed'},
     (Common.DBotScore.NONE, "The queried Domain is not listed on SURBL")),
    ({'surbl': 'listed'},
     (Common.DBotScore.BAD, "The queried Domain is listed on SURBL")),
    ({'spamhaus_dbl': 'spammer_domain'},
     (Common.DBotScore.BAD, "The queried Domain is a known spammer domain")),
    ({'spamhaus_dbl': 'not_listed'},
     (Common.DBotScore.NONE, "The queried Domain is not listed on Spamhaus DBL")),
    ({},
     (Common.DBotScore.GOOD, "There is no information about Domain in the blacklist")),
]


@pytest.mark.parametrize('blacklist,excepted_output', domain_command_test_reliability_dbot_score)
def test_domain_reliability_dbot_score(blacklist, excepted_output):
    """

    Given:
        - Domain blacklist from URLhaus database.

    When:
        - Calculating dbot score.

    Then:
        - Successes with right dbot score.

    """

    output = URLHaus.calculate_dbot_score('domain', blacklist)
    for i in range(len(excepted_output)):
        assert output[i] == excepted_output[i]


domain_command_test_create_relationships = [
    (True, 1),
    (False, 1),
    (True, 22),
    (False, 22),
    (True, 1000),
    (False, 1000),
    (True, 1),
    (False, 1),
    (True, 22),
    (False, 22),
    (True, 1000),
    (False, 1000),
]


@pytest.mark.parametrize('create_relationship,max_num_relationships',
                         domain_command_test_create_relationships)
def test_domain_command_test_create_relationships(create_relationship, max_num_relationships):
    """

    Given:
        - Blacklist status.

    When:
        - Adding tags from blacklist if they have relevant information.

    Then:
        - Add blacklist status information to the tags list.

    """
    urls = [{
        'url': f'test_url{i}',
    } for i in range(10000)]  # Large amounts of urls
    domain = "test_domain"
    excepted_output = []
    if create_relationship:
        excepted_output.extend([{
            "Relationship": 'hosts',
            "EntityA": domain,
            "EntityAType": 'Domain',
            "EntityB": urls[i].get('url'),
            "EntityBType": 'URL',
        } for i in range(max_num_relationships)])
    kwargs = {'create_relationships': create_relationship, 'max_num_of_relationships': max_num_relationships}
    results = URLHaus.domain_create_relationships(urls, domain, **kwargs)
    assert len(results) == len(excepted_output)
    for i in range(len(results)):
        assert results[i] == excepted_output[i]


domain_add_tags = [
    ('spammer_domain', ['spammer']),
    ('phishing_domain', ['phishing']),
    ('botnet_cc_domain', ['botnet']),
    ('listed', []),
    ('not listed', []),
    ('', []),
    (None, []),
]


@pytest.mark.parametrize('blacklist_status,excepted_output',
                         domain_add_tags)
def test_domain_add_tags(blacklist_status, excepted_output):
    """

    Given:
        - Create relationship table(T/F),max number of relationships(Limited to 1000).

    When:
        - Creating relationships table for domain command.

    Then:
        - Return indicators relationships table {Relationship,EntityA,EntityAType,EntityB,EntityBType}.

    """
    tags = []
    URLHaus.domain_add_tags(blacklist_status, tags)
    assert tags == excepted_output


def test_file_reliability_dbot_score():
    """

    Given:
        - File.

    When:
        - Calculating dbot score.

    Then:
        - Return Bad sbot score.

    """
    dbot_score = URLHaus.calculate_dbot_score('file', '')
    assert dbot_score == Common.DBotScore.BAD


file_command_test_create_relationships = [
    (True, 1),
    (True, 22),
    (False, 22),
    (True, 1000),
    (False, 1000),
]


@pytest.mark.parametrize('create_relationship,max_num_relationships',
                         file_command_test_create_relationships)
def test_file_create_relationships(create_relationship, max_num_relationships):
    """

    Given:
        - Create relationship table(T/F), max number of relationships(Limited to 1000).

    When:
        - Creating relationships table for file command.

    Then:
        - Return indicators relationships table {Relationship,EntityA,EntityAType,EntityB,EntityBType}.

    """
    urls = [{
        'url': f'test_url{i}',
    } for i in range(10000)]  # Large amounts of urls
    file = "123123123123123123123"
    sig = "test_signature"
    excepted_output = []
    if create_relationship:
        excepted_output = [{
            "Relationship": 'indicator-of',
            "EntityA": file,
            "EntityAType": 'File',
            "EntityB": sig,
            "EntityBType": 'Malware',
        }]
        excepted_output.extend([{
            "Relationship": 'related-to',
            "EntityA": file,
            "EntityAType": 'File',
            "EntityB": urls[i].get('url'),
            "EntityBType": 'URL',
        } for i in range(max_num_relationships - 1)])
    kwargs = {'create_relationships': create_relationship, 'max_num_of_relationships': max_num_relationships}
    results = URLHaus.file_create_relationships(file=file, urls=urls, sig=sig, **kwargs)
    assert len(results) == len(excepted_output)
    for i in range(len(results)):
        assert results[i] == excepted_output[i]
