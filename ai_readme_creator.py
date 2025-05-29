import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from pathlib import Path
from tempfile import mkdtemp
import os, json
import requests
import base64
from urllib.parse import urlparse
from typing import Dict, List, Optional


load_dotenv()

endpoint = os.getenv("ENDPOINT")
model_name = os.getenv("MODEL")
deployment =  os.getenv("MODEL")

subscription_key = os.getenv("SUBSCRIPTION_KEY")
api_version = os.getenv("API_VERSION")

github_token = os.getenv('GITHUB_TOKEN')

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

token = os.getenv('GITHUB_TOKEN')
headers = {}
if token:
    headers['Authorization'] = f'token {token}'
    headers['Accept'] = 'application/vnd.github.v3+json'


def parse_github_url(repo_url: str) -> Dict[str, str]:
        """Parse GitHub repository URL to extract owner and repo name."""
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            return {
                'owner': path_parts[0],
                'repo': path_parts[1]
            }
        else:
            raise ValueError("Invalid GitHub repository URL")
def get_repo_info(owner: str, repo: str) -> Dict:
    """Get basic repository information."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 404:
        raise Exception("Repository not found or access denied. Check if repo is private and provide token.")
    elif response.status_code != 200:
        raise Exception(f"Failed to fetch repo info: {response.status_code}")
    
    return response.json()

def get_file_tree(owner: str, repo: str, path: str = "") -> List[Dict]:
    """Recursively get all files and folders in the repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []
    
    items = response.json()
    file_tree = []
    
    for item in items:
        if item['type'] == 'file':
            file_tree.append({
                'name': item['name'],
                'path': item['path'],
                'type': 'file',
                'size': item['size'],
                'download_url': item.get('download_url')
            })
        elif item['type'] == 'dir':
            file_tree.append({
                'name': item['name'],
                'path': item['path'],
                'type': 'dir'
            })
            # Recursively get subdirectory contents (limit depth to avoid API limits)
            if path.count('/') < 2:  # Limit recursion depth
                file_tree.extend(get_file_tree(owner, repo, item['path']))
    
    return file_tree

def get_key_file_contents(owner: str, repo: str, file_tree: List[Dict]) -> Dict[str, str]:
    """Get contents of key files for better analysis."""
    key_files = ['package.json', 'requirements.txt', 'setup.py', 'Cargo.toml', 'go.mod', 'pom.xml', 'README.md', 'LICENSE']
    file_contents = {}
    
    for item in file_tree:
        if item['type'] == 'file' and item['name'] in key_files:
            try:
                if item.get('download_url'):
                    response = requests.get(item['download_url'], headers=headers)
                    if response.status_code == 200:
                        # Limit content size to avoid token limits
                        content = response.text[:2000]
                        file_contents[item['name']] = content
            except Exception as e:
                print(f"Error reading {item['name']}: {e}")
    
    return file_contents

def analyze_repository_with_llm(repo_data: Dict, file_tree: List[Dict], file_contents: Dict[str, str]) -> Dict:
        """Use LLM to analyze the repository structure and purpose."""
        
        # Prepare file structure summary
        file_structure = _create_file_structure_summary(file_tree)
        
        # Create analysis prompt
        analysis_prompt = f"""
        Analyze this GitHub repository and provide a structured analysis:

        Repository Name: {repo_data['name']}
        Description: {repo_data.get('description', 'No description provided')}
        Language: {repo_data.get('language', 'Not specified')}
        Stars: {repo_data.get('stargazers_count', 0)}
        Forks: {repo_data.get('forks_count', 0)}

        File Structure:
        {file_structure}

        Key File Contents:
        {_format_file_contents(file_contents)}

        Please provide a JSON response with the following structure:
        {{
            "project_type": "Brief description of what type of project this is",
            "main_purpose": "What does this project do?",
            "technologies": ["list", "of", "technologies", "used"],
            "key_features": ["list", "of", "main", "features"],
            "target_audience": "Who would use this project?",
            "complexity_level": "beginner/intermediate/advanced",
            "installation_type": "pip/npm/docker/manual/etc"
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a senior software engineer analyzing GitHub repositories. Provide accurate, concise analysis in valid JSON format."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content
            # Extract JSON from response
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            json_str = analysis_text[start_idx:end_idx]
            
            return json.loads(json_str)
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            return {
                "project_type": "Unknown",
                "main_purpose": "Purpose not determined",
                "technologies": [],
                "key_features": [],
                "target_audience": "Developers",
                "complexity_level": "intermediate",
                "installation_type": "manual"
            }

def generate_readme_with_llm(repo_data: Dict, file_tree: List[Dict], analysis: Dict) -> str:
        """Use LLM to generate a comprehensive README."""
        
        file_structure = _create_file_structure_summary(file_tree)
        
        readme_prompt = f"""
        Create a comprehensive, professional README.md file for this GitHub repository:

        Repository Information:
        - Name: {repo_data['name']}
        - Description: {repo_data.get('description', 'No description provided')}
        - Language: {repo_data.get('language', 'Not specified')}
        - Stars: {repo_data.get('stargazers_count', 0)}
        - Forks: {repo_data.get('forks_count', 0)}
        - License: {repo_data.get('license', {}).get('name', 'Not specified') if repo_data.get('license') else 'Not specified'}
        - Clone URL: {repo_data['clone_url']}

        Project Analysis:
        - Type: {analysis['project_type']}
        - Purpose: {analysis['main_purpose']}
        - Technologies: {', '.join(analysis['technologies'])}
        - Key Features: {', '.join(analysis['key_features'])}
        - Target Audience: {analysis['target_audience']}
        - Complexity: {analysis['complexity_level']}
        - Installation Type: {analysis['installation_type']}

        File Structure:
        {file_structure}

        Please create a README.md that includes:
        1. An engaging title and description
        2. Badges (stars, forks, license, language)
        3. Table of contents
        4. Clear installation instructions based on the project type
        5. Usage examples
        6. Project structure overview
        7. Features list
        8. Contributing guidelines
        9. License information
        10. Repository statistics

        Make it professional, engaging, and easy to understand. Use proper markdown formatting.
        Include relevant emojis to make it visually appealing.
        Tailor the content specifically to this project's purpose and audience.
        """
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in creating excellent README files for GitHub repositories. Create comprehensive, well-structured, and engaging documentation."},
                    {"role": "user", "content": readme_prompt}
                ],
                temperature=0.4,
                max_tokens=3000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating README with LLM: {str(e)}"
    
def _create_file_structure_summary(file_tree: List[Dict], max_files: int = 30) -> str:
    """Create a concise file structure summary."""
    structure_lines = []
    dirs = set()
    files = []
    
    for item in file_tree:
        if item['type'] == 'dir':
            dirs.add(item['path'])
        else:
            files.append(item['path'])
    
    # Add directories
    for dir_path in sorted(list(dirs))[:10]:  # Limit directories
        structure_lines.append(f"📁 {dir_path}/")
    
    # Add files
    for file_path in sorted(files)[:max_files]:  # Limit files
        structure_lines.append(f"📄 {file_path}")
    
    if len(files) > max_files:
        structure_lines.append(f"... and {len(files) - max_files} more files")
    
    return "\n".join(structure_lines)
    
def _format_file_contents(file_contents: Dict[str, str]) -> str:
    """Format file contents for the prompt."""
    formatted = []
    for filename, content in file_contents.items():
        formatted.append(f"\n--- {filename} ---")
        formatted.append(content[:500] + "..." if len(content) > 500 else content)
    return "\n".join(formatted)
    
def generate_readme(repo_url: str) -> str:
    """Generate a comprehensive README using LLM for the repository."""
    try:
        # Parse repository URL
        repo_info = parse_github_url(repo_url)
        owner, repo = repo_info['owner'], repo_info['repo']
        
        # Use stderr for progress messages so they don't mix with the output
        import sys
        sys.stderr.write(f"🔍 Analyzing repository: {owner}/{repo}\n")
        sys.stderr.flush()
        
        # Get repository information
        repo_data = get_repo_info(owner, repo)
        sys.stderr.write("📚 Repository data fetched\n")
        sys.stderr.flush()
        
        # Get file tree
        file_tree = get_file_tree(owner, repo)
        sys.stderr.write(f"📂 Found {len(file_tree)} files and folders\n")
        sys.stderr.flush()
        
        # Get key file contents
        file_contents = get_key_file_contents(owner, repo, file_tree)
        sys.stderr.write(f"📄 Analyzed {len(file_contents)} key files\n")
        sys.stderr.flush()
        
        # Analyze with LLM
        sys.stderr.write("🤖 Analyzing repository with AI...\n")
        sys.stderr.flush()
        analysis = analyze_repository_with_llm(repo_data, file_tree, file_contents)
        
        # Generate README with LLM
        sys.stderr.write("✍️ Generating README with AI...\n")
        sys.stderr.flush()
        readme_content = generate_readme_with_llm(repo_data, file_tree, analysis)
        
        return readme_content
        
    except Exception as e:
        return f"Error generating README: {str(e)}"


def main():
    """CLI fallback for the LLM-powered README generator."""
    print("AI-Powered GitHub README Generator (CLI Mode)")
    print("=" * 50)

    # Check for API key
    if not subscription_key:
        print("OPENAI_API_KEY not found in .env file!")
        return

    # Get repository URL
    repo_url = input("\nEnter GitHub repository URL: ").strip()
    if not repo_url:
        print("Repository URL is required!")
        return

    # Generate README
    try:
        print("\nGenerating README...")
        readme_content = generate_readme(repo_url)

        # Save to file
        output_file = "ai_generated_README.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"\nREADME generated successfully! Saved to: {output_file}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # When called from Next.js API
        repo_url = sys.argv[1]
        try:
            readme_content = generate_readme(repo_url)
            print(readme_content)  # This will be captured by Node.js
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)
    else:
        # Interactive CLI mode
        main()