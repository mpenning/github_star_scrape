.DEFAULT_GOAL := repo-push

.PHONY: repo-push
repo-push:
	@echo ">> checkout the main branch, push to origin/main, switch back to the develop branch"
	ping -q -c1 -W1 4.2.2.2                   # quiet ping...
	-git checkout master || git checkout main # Add dash to ignore checkout fails
	# Now the main branch is checked out...
	THIS_BRANCH=$(shell git branch --show-current)  # assign 'main' to $THIS_BRANCH
	git merge @{-1}                           # merge the previous branch into main...
	# force push to origin / $THIS_BRANCH
	git push --force-with-lease origin $(THIS_BRANCH)
	git checkout @{-1}                        # checkout the previous branch...

