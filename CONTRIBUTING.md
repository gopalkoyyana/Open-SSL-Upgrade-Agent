# Contributing to OpenSSL Upgrade Agent

Thank you for your interest in contributing to the OpenSSL Upgrade Agent! This document provides guidelines and instructions for contributing to this project.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with the following information:

- **Clear title** describing the issue
- **Detailed description** of the problem
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Environment details**:
  - Operating System (Windows/Linux/macOS version)
  - Python version
  - OpenSSL version (if applicable)
- **Error messages** or logs (if any)

### Suggesting Enhancements

We welcome feature requests! Please create an issue with:

- **Clear title** describing the enhancement
- **Detailed description** of the proposed feature
- **Use case** - why this feature would be useful
- **Possible implementation** (if you have ideas)

### Pull Requests

We actively welcome your pull requests!

1. **Fork the repository** and create your branch from `main`
2. **Make your changes**:
   - Write clear, commented code
   - Follow the existing code style
   - Add tests if applicable
3. **Test your changes** thoroughly on your target platform(s)
4. **Update documentation** if you've changed functionality
5. **Commit your changes** with clear, descriptive commit messages
6. **Push to your fork** and submit a pull request

#### Pull Request Guidelines

- **One feature per PR** - Keep pull requests focused
- **Descriptive title** - Clearly describe what the PR does
- **Detailed description** - Explain the changes and why they're needed
- **Reference issues** - Link to related issues (e.g., "Fixes #123")
- **Test on multiple platforms** - If possible, test on Windows, Linux, and macOS

## 💻 Development Setup

### Prerequisites

- Python 3.6 or higher
- Git
- Access to a test environment (VM recommended for testing system changes)

### Setting Up Your Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Open-SSL-Upgrade-Agent.git
cd Open-SSL-Upgrade-Agent

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies (if any)
pip install -r requirements.txt  # If we add this file later
```

### Testing Your Changes

**⚠️ IMPORTANT: Never test on production systems!**

- Use virtual machines or test environments
- Test on multiple operating systems if possible
- Verify backup creation works correctly
- Test rollback functionality
- Check log file generation

## 📝 Code Style Guidelines

- **PEP 8** - Follow Python's style guide
- **Clear variable names** - Use descriptive names
- **Comments** - Add comments for complex logic
- **Docstrings** - Document functions and classes
- **Error handling** - Include proper exception handling
- **Logging** - Use the logging module appropriately

### Example Code Style

```python
def backup_file(source_path, backup_dir):
    """
    Create a backup of the specified file.
    
    Args:
        source_path (str): Path to the file to backup
        backup_dir (str): Directory to store the backup
        
    Returns:
        str: Path to the backup file
        
    Raises:
        IOError: If backup creation fails
    """
    try:
        # Implementation here
        pass
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise
```

## 🔍 Code Review Process

1. **Automated checks** - Ensure your code passes any automated tests
2. **Maintainer review** - A project maintainer will review your PR
3. **Feedback** - Address any requested changes
4. **Approval** - Once approved, your PR will be merged

## 🌟 Areas for Contribution

We especially welcome contributions in these areas:

- **Platform support** - Testing and fixes for different OS versions
- **Error handling** - Improved error messages and recovery
- **Documentation** - Tutorials, examples, translations
- **Testing** - Unit tests, integration tests
- **Features** - New functionality (discuss in an issue first)
- **Bug fixes** - Always welcome!

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Our Standards

- **Be respectful** - Treat everyone with respect
- **Be constructive** - Provide helpful feedback
- **Be patient** - Remember that everyone has different experience levels
- **Be open-minded** - Consider different perspectives

### Unacceptable Behavior

- Harassment or discriminatory language
- Personal attacks or trolling
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

## 📞 Questions?

If you have questions about contributing, feel free to:

- Open an issue with the `question` label
- Reach out to the maintainers

## 🙏 Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort!

---

**Happy Contributing! 🚀**
