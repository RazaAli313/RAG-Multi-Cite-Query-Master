#!/bin/bash

REQ_FILES=(
  "/code/config/requirements/base"
  "/code/config/requirements/dev"
  "/code/config/requirements/test"
  "/code/config/requirements/stage"
  "/code/config/requirements/prod"
)

for f in "${REQ_FILES[@]}"; do
  pip-compile --generate-hashes --resolver=backtracking -o ${f}.txt ${f}.in || exit 1;
done
