import shodan
import socket
import requests
import os
import time

# Note: You'll need to install the shodan library: pip install shodan
# Also, you need a Shodan API key. Sign up at https://account.shodan.io/ and get one.
# Replace 'YOUR_SHODAN_API_KEY' with your actual key.
# Warning: Paginating through all results will consume API credits (1 per page).

API_KEY = 'PUT_API_KEY_HERE'

def is_domain_alive(hostname):
    """
    Checks if a domain is alive by trying to resolve it and then sending an HTTP/HTTPS request.
    Returns True if it gets any response (even error codes), False otherwise.
    """
    try:
        # Resolve the hostname to IP
        socket.gethostbyname(hostname)
        
        # Try HTTP and HTTPS
        for protocol in ['http', 'https']:
            url = f"{protocol}://{hostname}"
            response = requests.get(url, timeout=5)
            if response.status_code:  # Any status code means it's responding
                return True
    except (socket.gaierror, requests.exceptions.RequestException):
        return False
    return False

def main():
    # Prompt for Shodan dork
    dork = input("Enter your Shodan dork: ").strip()
    
    # Prompt for output file path
    output_path = input("Enter the output file path (e.g., /home/packetsurfer/desktop/subs.txt): ").strip()
    
    # Validate output path directory
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        print(f"Directory {output_dir} does not exist. Creating it...")
        os.makedirs(output_dir)
    
    # Initialize Shodan API
    api = shodan.Shodan(API_KEY)
    
    try:
        hostnames = set()
        page = 1
        total_results = None
        
        while True:
            print(f"Fetching page {page}...")
            try:
                result = api.search(dork, page=page)
                
                # Set total results on first page
                if page == 1:
                    total_results = result.get('total', 0)
                    print(f"Total results expected: {total_results}")
                
                matches = result.get('matches', [])
                print(f"Page {page} returned {len(matches)} matches")
                
                # Extract hostnames and domains
                for match in matches:
                    if 'hostnames' in match:
                        hostnames.update(match['hostnames'])
                    if 'domains' in match:
                        hostnames.update(match['domains'])
                
                # Check if we've reached the end
                if not matches or (total_results and page * 100 >= total_results):
                    print(f"Reached end of results after page {page}. Total matches: {total_results}")
                    break
                
                page += 1
                time.sleep(2)  # Increased to 2 seconds to avoid rate limits
            
            except shodan.APIError as e:
                error_msg = str(e).lower()
                if "no more results" in error_msg or "no information available" in error_msg:
                    print(f"No more results found after page {page}.")
                    break
                elif "api key" in error_msg or "unauthorized" in error_msg:
                    print(f"API error: Invalid or unauthorized API key. Please check your key at https://account.shodan.io/")
                    return
                elif "rate limit" in error_msg:
                    print(f"Hit API rate limit. Waiting 10 seconds before retrying page {page}...")
                    time.sleep(10)
                    continue
                else:
                    print(f"API error on page {page}: {e}")
                    break
        
        if not hostnames:
            print("No hostnames or domains found in the results.")
            return
        
        print(f"Found {len(hostnames)} unique hostnames/domains across {page} pages. Checking which are alive...")
        
        alive_domains = []
        for hostname in sorted(hostnames):
            print(f"Checking {hostname}...")
            if is_domain_alive(hostname):
                alive_domains.append(hostname)
                print(f"{hostname} is alive.")
            else:
                print(f"{hostname} is not responding.")
        
        if alive_domains:
            print(f"\nFound {len(alive_domains)} alive domains:")
            for domain in alive_domains:
                print(domain)
            
            # Save to file
            try:
                with open(output_path, 'w') as f:
                    for domain in alive_domains:
                        f.write(f"{domain}\n")
                print(f"\nAlive domains saved to {output_path}")
            except Exception as e:
                print(f"Error writing to {output_path}: {e}")
        else:
            print("\nNo alive domains found.")
    
    except shodan.APIError as e:
        print(f"Shodan API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
