import json

file_path = r'c:\Users\asus\Documents\003. YouTubeSummaryAgent\test_hierarchical_v3.json'

with open(file_path, encoding='utf-8') as f:
    d = json.load(f)

ss = d.get('structured_summary', {})

print('=== Hierarchical Test Result ===')
print('Success:', d.get('success'))
print('Notion URL:', d.get('notion_url', ''))
print()

print('=== sections Field Check ===')
sections = ss.get('sections', [])
print('Sections count:', len(sections))
print('Main Topics (legacy):', len(ss.get('main_topics', [])))
print()

if sections:
    print('=== Section Details ===')
    for i, s in enumerate(sections):
        subtopics = s.get('subtopics', [])
        print(f'{i+1}. {s.get("section_title")}: {len(subtopics)} subtopics')
else:
    print('No sections found - checking main_topics instead')
    main_topics = ss.get('main_topics', [])
    if main_topics:
        print(f'Found {len(main_topics)} main_topics')
        for i, t in enumerate(main_topics[:5]):
            print(f'{i+1}. {t.get("title", "N/A")}')
