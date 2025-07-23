Run python generate_blog_posts.py
  python generate_blog_posts.py
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.9.23/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.9.23/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.9.23/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.9.23/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.9.23/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.9.23/x64/lib
    GOOGLE_API_KEY: ***
    GITHUB_REPO_OWNER: Codestrym
    GITHUB_REPO_NAME: affiliate
    GITHUB_BRANCH: main
Traceback (most recent call last):
Found 6 new post(s) to process from blog.csv.

Processing new row 0: Social Text='A SMART #WATCH ⌚ is essential these days. Get your amazing #Deal using our affiliate link!', AI Keyword='smartwatch'
  File "/home/runner/work/affiliate/affiliate/generate_blog_posts.py", line 472, in <module>
    main()
  File "/home/runner/work/affiliate/affiliate/generate_blog_posts.py", line 378, in main
    generated_text_with_summary = call_gemini_api(prompt_text)
NameError: name 'prompt_text' is not defined
Error: Process completed with exit code 1.
