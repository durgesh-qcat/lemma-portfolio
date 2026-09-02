#!/bin/sh
set -u

lemma_portfolio_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$lemma_portfolio_dir"
verification_status=0
python3 verify_release.py || verification_status=$?

if [ -t 0 ]; then
  printf '\nVerification finished. Press Return to close.\n'
  read -r lemma_portfolio_reply
fi

exit "$verification_status"
