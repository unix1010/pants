import React from 'react';
import ScribeClient from 'scribe-js-client';

import styles from './styles.css';

class Tweet extends React.Component {
  componentDidMount() {
    ScribeClient.log({client: 'm5', action: 'impression'});
  }

  render() {
    const actions = this.props.withActions ? <a href="#">fav</a> : null;

    return (<div className={styles.tweet}>
      <h1>THIS IS A TWEET</h1>
      {actions}
    </div>);
  }
}

export default Tweet;
