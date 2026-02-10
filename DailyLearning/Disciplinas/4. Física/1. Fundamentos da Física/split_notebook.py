
import re
import os

source_file = "/home/Pedro/Documentos/Obsidian/SmartNoteBrain/DailyLearning/Disciplinas/4. Física/1. Fundamentos da Física/4. - 4.1.10..md"
target_dir = os.path.dirname(source_file)

with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Extract topics from the first code block
# The block starts with ``` and ends with ```. It contains lines like:
# 4. **Ordens de Grandeza e Estimativas** (Avaliação ...),,,,.
# We need to capture the number, the title, and the full line to use for replacement in prompts.

# Regex to find the first code block
first_code_block_match = re.search(r'```(.*?)```', content, re.DOTALL)
if not first_code_block_match:
    print("Error: Could not find the first code block.")
    exit(1)

first_code_block_content = first_code_block_match.group(1).strip()
topics_raw_lines = [line.strip() for line in first_code_block_content.split('\n') if line.strip()]

topics = []
for line in topics_raw_lines:
    # Match: "4. **Title** (Desc),,,,."
    # We want to extract "4", "Ordens de Grandeza e Estimativas", and the full line description.
    match = re.match(r'(\d+)\.\s*\*\*(.*?)\*\*', line)
    if match:
        number = match.group(1)
        title = match.group(2)
        topics.append({
             'number': number, 
             'title': title, 
             'full_line': line
        })

print(f"Found {len(topics)} topics.")

# 2. Prepare the template
# Remove the first code block (including fences)
# The `count=1` ensures we only remove the first occurrence (which is the list of topics)
content_template = content.replace(first_code_block_match.group(0), "", 1)

# Remove extra newlines that might have been left behind
content_template = re.sub(r'---\s*\n\s*\n\s*\n##', '---\n\n##', content_template)


# 3. Create files
for topic in topics:
    new_filename = f"{topic['number']}. {topic['title']}.md"
    new_filepath = os.path.join(target_dir, new_filename)
    
    current_content = content_template
    
    # Update NotebookLM link/title in frontmatter if present?
    # The original has: NotebookLM: "[4. - 10.](<url>)"
    # We probably want to keep the URL but change the text? Or just keep it as is?
    # The request doesn't specify, but usually we want to keep the link.
    # Let's simple update the text inside [] to the new title.
    # Regex for NotebookLM line: `NotebookLM: "\[.*?\]`
    current_content = re.sub(r'(NotebookLM:\s*"\[)(.*?)(\])', f'\\1{topic["number"]}. {topic["title"]}\\3', current_content)

    # Replace the list of topics in the prompts
    # The prompts have a section:
    # Tópico(s) deste notebook (Somente esses):
    # <List of all topics>
    # ```
    # We need to replace <List of all topics> with ONLY the current topic line.
    
    # We can identify the list block in the prompts. It seems to be the exact same content as the first code block.
    # However, formatting might differ slightly (tabs/spaces).
    # Let's do a regex replacement for the block of topics within the prompts.
    
    # Construct a regex that matches the list of topics. 
    # Since we know the exact lines from `topics_raw_lines`, we can try to find that block.
    # But indentation might be an issue.
    # Safe approach: Search for "Tópico(s) deste notebook (Somente esses):" and then replace everything until the next "```" or end of section.
    
    def replace_topic_list(match):
        header = match.group(1)
        return header + "\n" + topic['full_line'] + "\n"

    # Pattern: 
    # (Tópico\(s\) deste notebook \(Somente esses\):\n)  <-- Group 1
    # (.*?)                                            <-- Group 2 (The list)
    # (?=```)                                           <-- Lookahead for end of block
    
    current_content = re.sub(
        r'(Tópico\(s\) deste notebook \(Somente esses\):\n)(.*?)(?=```)', 
        replace_topic_list, 
        current_content, 
        flags=re.DOTALL
    )

    with open(new_filepath, 'w', encoding='utf-8') as f:
        f.write(current_content)
    
    print(f"Created {new_filename}")

# 4. Verification and Deletion
# Only delete if all files were created
if len(os.listdir(target_dir)) >= len(topics) + 1: # +1 for original file (sanity check)
     print("Removing original file...")
     os.remove(source_file)
     print("Done.")

